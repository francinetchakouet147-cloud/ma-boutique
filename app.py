from flask import Flask, render_template, request, jsonify
import os, json
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)

# --- CONNEXION MONGODB ATLAS ---
MONGO_URI = os.environ.get("MONGODB_URI", "MET_TON_LIEN_ICI_TEMPORAIREMENT")
client_mongo = MongoClient(MONGO_URI)
db_mongo = client_mongo["ma-boutique"]
clients_col = db_mongo["clients"]
stock_col = db_mongo["stock"]
mouv_col = db_mongo["mouvements"]
factures_col = db_mongo["factures"]
depenses_col = db_mongo["depenses"]

def init_db():
    if not clients_col.find_one({"nom":"aurelie"}):
        clients_col.insert_one({"nom":"aurelie","tel":"000","boutique":"Admin","pass":"aurelie123","premiere":0,"bloque":0})

init_db()

@app.route('/')
def login(): return render_template('login.html')
@app.route('/admin')
def admin(): return render_template('admin.html')
@app.route('/boutique')
def boutique_page(): return render_template('boutique.html')
@app.route('/enregistrer')
def enregistrer(): return render_template('enregistrer.html')
@app.route('/categories')
def categories(): return render_template('categories.html')
@app.route('/statistiques')
def statistiques(): return render_template('statistiques.html')
@app.route('/historique')
def historique(): return render_template('historique.html')
@app.route('/stock-faible')
def stock_faible(): return render_template('stock-faible.html')
@app.route('/ventes')
def ventes(): return render_template('ventes.html')
@app.route('/commande')
def commande(): return render_template('commande.html')
@app.route('/factures')
def factures_page(): return render_template('factures.html')
@app.route('/depenses')
def depenses_page(): return render_template('depenses.html')

# API LOGIN
@app.route('/api/login', methods=['POST'])
def api_login():
    d=request.json; nom=d.get('nom','').lower(); pas=d.get('pass','')
    if nom=='aurelie' and pas=='aurelie123': return jsonify({'ok':True,'role':'admin'})
    cl=clients_col.find_one({"nom": nom})
    if not cl: return jsonify({'ok':False,'msg':'Client inconnu'})
    if cl.get('bloque'): return jsonify({'ok':False,'msg':'Compte bloqué'})
    if cl.get('pass')!=pas: return jsonify({'ok':False,'msg':'Mauvais mot de passe'})
    cl['_id']=str(cl['_id'])
    return jsonify({'ok':True,'role':'client','premiere':bool(cl.get('premiere')), 'client':cl})

@app.route('/api/clients')
def api_clients():
    rows=list(clients_col.find({"nom":{"$ne":"aurelie"}}))
    for r in rows: r['_id']=str(r['_id']); r['id']=r['_id']
    return jsonify(rows)

@app.route('/api/clients', methods=['POST'])
def api_add():
    d=request.json
    try:
        clients_col.insert_one({"nom":d['nom'].lower(),"tel":d['tel'],"boutique":d['boutique'],"pass":"1234","premiere":1,"bloque":0})
    except: return jsonify({'ok':False,'msg':'Nom déjà utilisé'})
    return jsonify({'ok':True})

@app.route('/api/clients/<id>', methods=['PUT','DELETE'])
def api_edit(id):
    try:
        oid=ObjectId(id)
    except:
        # si ancien id int
        clients_col.delete_one({"nom":id}); return jsonify({'ok':True})
    if request.method=='DELETE':
        clients_col.delete_one({"_id":oid})
    else:
        d=request.json
        if 'bloque' in d: clients_col.update_one({"_id":oid},{"$set":{"bloque":int(d['bloque'])}})
        if 'reset' in d: clients_col.update_one({"_id":oid},{"$set":{"pass":"1234","premiere":1}})
        if 'newpass' in d: clients_col.update_one({"_id":oid},{"$set":{"pass":d['newpass'],"premiere":0}})
        if 'nom' in d: clients_col.update_one({"_id":oid},{"$set":{"nom":d['nom'],"tel":d['tel'],"boutique":d['boutique']}})
    return jsonify({'ok':True})

# Le reste stock/mouvements/factures/depenses je te le laisse en MongoDB aussi
@app.route('/api/stock')
def api_stock():
    b=request.args.get('boutique','')
    stock=list(stock_col.find({"boutique":b})); 
    for s in stock: s['id']=str(s['_id'])
    mouv=list(mouv_col.find({"boutique":b}).sort("_id",-1))
    for m in mouv: m['id']=str(m['_id'])
    return jsonify({'stock':stock,'mouvements':mouv})

@app.route('/api/stock', methods=['POST'])
def api_stock_save():
    d=request.json
    if d.get('id') and len(d.get('id'))==24:
        try: stock_col.update_one({"_id":ObjectId(d['id'])},{"$set":{"groupe":d['groupe'],"nom":d['nom'],"qte":d['qte'],"unite":d['unite'],"achat":d['achat'],"vente":d['vente']}}); return jsonify({'ok':True})
        except: pass
    if d.get('id'): stock_col.update_one({"boutique":d['boutique'],"nom":d['nom']},{"$set":{"groupe":d['groupe'],"qte":d['qte'],"unite":d['unite'],"achat":d['achat'],"vente":d['vente']}}, upsert=True)
    else: stock_col.insert_one({"boutique":d['boutique'],"groupe":d['groupe'],"nom":d['nom'],"qte":d['qte'],"unite":d['unite'],"achat":d['achat'],"vente":d['vente']})
    return jsonify({'ok':True})

@app.route('/api/stock/<id>', methods=['DELETE'])
def api_stock_del(id):
    try: stock_col.delete_one({"_id":ObjectId(id)})
    except: stock_col.delete_one({"_id":id})
    return jsonify({'ok':True})

@app.route('/api/mouvement', methods=['POST'])
def api_mouv():
    d=request.json
    try: row=stock_col.find_one({"_id":ObjectId(d['id'])})
    except: row=stock_col.find_one({"boutique":d['boutique'],"nom":d['produit']})
    if not row: return jsonify({'ok':False})
    nq=row['qte']-float(d['qte']) if d['type']=='Vendu' else row['qte']+float(d['qte'])
    if nq<0: nq=0
    stock_col.update_one({"_id":row['_id']},{"$set":{"qte":nq}})
    now=datetime.now()
    mouv_col.insert_one({"boutique":d['boutique'],"produit":d['produit'],"groupe":row.get('groupe'),"type":d['type'],"qte":float(d['qte']),"achat":row.get('achat'),"vente":row.get('vente'),"date":now.strftime('%Y-%m-%d'),"heure":now.strftime('%H:%M'),"datetime":now.isoformat()})
    return jsonify({'ok':True})

@app.route('/api/factures', methods=['GET','POST'])
def api_factures():
    if request.method == 'POST':
        d=request.json
        factures_col.insert_one({"boutique":d['boutique'],"num":d['num'],"client":d['client'],"tel":d['tel'],"total":d['total'],"produits":json.dumps(d['produits']),"date":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return jsonify({"ok":True})
    else:
        b=request.args.get('boutique'); rows=list(factures_col.find({"boutique":b}).sort("_id",-1))
        for r in rows: r['id']=str(r['_id']); r['_id']=str(r['_id'])
        return jsonify(rows)

@app.route('/api/facture/<id>', methods=['DELETE'])
def del_facture(id):
    try: factures_col.delete_one({"_id":ObjectId(id)})
    except: pass
    return jsonify({"ok":True})

@app.route('/api/depenses', methods=['GET','POST'])
def api_depenses():
    if request.method == 'POST':
        d=request.json; now=datetime.now()
        depenses_col.insert_one({"boutique":d['boutique'],"motif":d['motif'],"categorie":d['categorie'],"montant":float(d['montant']),"date":now.strftime('%Y-%m-%d'),"heure":now.strftime('%H:%M'),"datetime":now.isoformat()})
        return jsonify({"ok":True})
    else:
        b=request.args.get('boutique'); rows=list(depenses_col.find({"boutique":b}).sort("datetime",-1))
        for r in rows: r['id']=str(r['_id'])
        today=datetime.now().date()
        jour=[x for x in rows if x['date']==today.isoformat()]
        semaine=[x for x in rows if datetime.fromisoformat(x['datetime']).date() >= today - timedelta(days=7)]
        mois=[x for x in rows if datetime.fromisoformat(x['datetime']).date() >= today - timedelta(days=30)]
        return jsonify({"all":rows,"jour":jour,"semaine":semaine,"mois":mois,"total_jour":sum(x['montant'] for x in jour),"total_semaine":sum(x['montant'] for x in semaine),"total_mois":sum(x['montant'] for x in mois)})

@app.route('/api/depenses/<id>', methods=['DELETE'])
def del_dep(id):
    try: depenses_col.delete_one({"_id":ObjectId(id)})
    except: pass
    return jsonify({"ok":True})

@app.route('/api/historique')
def api_histo():
    b=request.args.get('boutique','')
    all_mouv=list(mouv_col.find({"boutique":b}).sort("datetime",-1))
    all_dep=list(depenses_col.find({"boutique":b}).sort("datetime",-1))
    today=datetime.now().date()
    jour=[m for m in all_mouv if m['date']==today.isoformat()]
    semaine=[]
    for i in range(1,8):
        d=(today-timedelta(days=i)).isoformat()
        semaine.extend([m for m in all_mouv if m['date']==d])
    dep_jour=[d for d in all_dep if d['date']==today.isoformat()]
    dep_semaine=[d for d in all_dep if datetime.fromisoformat(d['datetime']).date() >= today - timedelta(days=7)]
    benef_jour = sum((x.get('vente',0)-x.get('achat',0))*x.get('qte',0) for x in jour if x['type']=='Vendu')
    benef_semaine = sum((x.get('vente',0)-x.get('achat',0))*x.get('qte',0) for x in semaine if x['type']=='Vendu')
    dep_jour_total = sum(x['montant'] for x in dep_jour)
    dep_semaine_total = sum(x['montant'] for x in dep_semaine)
    mois=[]
    for w in range(4):
        debut=today-timedelta(days=7*(w+2)+1); fin=debut+timedelta(days=6)
        items=[m for m in all_mouv if debut.isoformat() <= m['date'] <= fin.isoformat()]
        dep_items=[d for d in all_dep if debut.isoformat() <= d['date'] <= fin.isoformat()]
        if items or dep_items:
            benef = sum((x.get('vente',0)-x.get('achat',0))*x.get('qte',0) for x in items if x['type']=='Vendu')
            dep = sum(x['montant'] for x in dep_items)
            mois.append({"label": f"Semaine {4-w} : {debut.strftime('%d/%m')} - {fin.strftime('%d/%m')}", "vendu": sum(x.get('qte',0) for x in items if x['type']=='Vendu'), "recharge": sum(x.get('qte',0) for x in items if x['type']=='Rechargé'), "items": items, "depenses": dep_items, "benef_brut": benef, "dep_total": dep, "benef_net": benef - dep})
    return jsonify({"jour":jour,"semaine":semaine,"mois":mois,"all":all_mouv,"dep_jour":dep_jour,"dep_semaine":dep_semaine,"benef_jour_brut":benef_jour,"benef_jour_net":benef_jour - dep_jour_total,"benef_semaine_brut":benef_semaine,"benef_semaine_net":benef_semaine - dep_semaine_total,"dep_jour_total":dep_jour_total,"dep_semaine_total":dep_semaine_total})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
