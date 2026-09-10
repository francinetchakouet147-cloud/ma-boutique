from flask import Flask, render_template, request, jsonify, send_from_directory
import os, json
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

MONGO_URI = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI")
if not MONGO_URI:
    raise Exception("MONGO_URI manquant")

client_mongo = MongoClient(MONGO_URI)
db_mongo = client_mongo["ma-boutique"]
clients_col = db_mongo["clients"]
stock_col = db_mongo["stock"]
mouv_col = db_mongo["mouvements"]
factures_col = db_mongo["factures"]
depenses_col = db_mongo["depenses"]
dettes_col = db_mongo["dettes"]
demande_crea_col = db_mongo["demandes_creation"]
demande_oublie_col = db_mongo["demandes_oublie"]

def serialize(doc):
    if not doc: return None
    doc['_id'] = str(doc['_id'])
    doc['id'] = doc['_id']
    return doc

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
@app.route('/dettes')
def dettes_page(): return render_template('dettes.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    d=request.json
    nom=d.get('nom','').lower().strip()
    pas=d.get('pass','').strip()
    if nom=='aurelie' and pas=='aurelie123':
        return jsonify({'ok':True,'role':'admin'})
    cl=clients_col.find_one({"nom": nom})
    if not cl: return jsonify({'ok':False,'msg':'Client inconnu'})
    if cl.get('bloque')==1: return jsonify({'ok':False,'msg':'Compte bloqué par admin'})
    if cl.get('pass')!=pas: return jsonify({'ok':False,'msg':'Mauvais mot de passe'})
    is_premiere = bool(cl.get('premiere')==1)
    cl_serialized = serialize(cl)
    if is_premiere: return jsonify({'ok':True,'role':'client','premiere':True, 'client':cl_serialized})
    return jsonify({'ok':True,'role':'client','premiere':False, 'client':cl_serialized})

# DEMANDE CREATION - AVEC MOT DE PASSE DU CLIENT
@app.route('/api/demande-creation', methods=['POST'])
def demande_creation():
    d=request.json
    demande_crea_col.insert_one({
        "nom_voulu": d.get('nom_voulu','').lower().strip(),
        "boutique": d.get('boutique','').strip(),
        "tel": d.get('tel','').strip(),
        "pass": d.get('pass','').strip(),
        "date": datetime.now().isoformat(),
        "statut": "en_attente"
    })
    return jsonify({'ok':True})

@app.route('/api/demandes-creation')
def list_demande_crea():
    rows=[serialize(r) for r in demande_crea_col.find({"statut":"en_attente"}).sort("_id",-1)]
    return jsonify(rows)

@app.route('/api/demandes-creation/<id>/accepter', methods=['POST'])
def accepter_crea(id):
    try: dem=demande_crea_col.find_one({"_id":ObjectId(id)})
    except: return jsonify({'ok':False})
    if not dem: return jsonify({'ok':False})
    if clients_col.find_one({"nom": dem['nom_voulu'].lower()}):
        return jsonify({'ok':False,'msg':'Nom déjà utilisé'})
    # Creation avec le mot de passe qu'il a choisi, pas de premiere
    clients_col.insert_one({
        "nom":dem['nom_voulu'].lower(),
        "tel":dem['tel'],
        "boutique":dem['boutique'],
        "pass":dem.get('pass','1234'),
        "premiere":0,
        "bloque":0
    })
    demande_crea_col.update_one({"_id":ObjectId(id)},{"$set":{"statut":"accepte"}})
    return jsonify({'ok':True})

@app.route('/api/demandes-creation/<id>', methods=['DELETE'])
def refuser_crea(id):
    try: demande_crea_col.delete_one({"_id":ObjectId(id)})
    except: pass
    return jsonify({'ok':True})

# DEMANDE OUBLIE
@app.route('/api/demande-oublie', methods=['POST'])
def demande_oublie():
    d=request.json
    demande_oublie_col.insert_one({
        "identifiant": d.get('identifiant','').strip(),
        "type": d.get('type',''),
        "date": datetime.now().isoformat(),
        "statut": "en_attente"
    })
    return jsonify({'ok':True})

@app.route('/api/demandes-oublie')
def list_oublie():
    rows=[serialize(r) for r in demande_oublie_col.find({"statut":"en_attente"}).sort("_id",-1)]
    return jsonify(rows)

@app.route('/api/demandes-oublie/<id>/reset', methods=['POST'])
def reset_oublie(id):
    try: dem=demande_oublie_col.find_one({"_id":ObjectId(id)})
    except: return jsonify({'ok':False})
    if dem and dem['type'] in ['pass','lesdeux']:
        cl=clients_col.find_one({"$or":[{"tel":dem['identifiant']},{"boutique":dem['identifiant']},{"nom":dem['identifiant'].lower()}]})
        if cl:
            clients_col.update_one({"_id":cl['_id']},{"$set":{"pass":"1234","premiere":1}})
    demande_oublie_col.update_one({"_id":ObjectId(id)},{"$set":{"statut":"traite"}})
    return jsonify({'ok':True})

@app.route('/api/demandes-oublie/<id>', methods=['DELETE'])
def del_oublie(id):
    try: demande_oublie_col.delete_one({"_id":ObjectId(id)})
    except: pass
    return jsonify({'ok':True})

@app.route('/api/clients')
def api_clients():
    q=request.args.get('q','').lower().strip()
    if q:
        rows=list(clients_col.find({"nom":{"$ne":"aurelie"}, "$or":[{"nom":{"$regex":q}},{"boutique":{"$regex":q}},{"tel":{"$regex":q}}]}))
    else:
        rows=list(clients_col.find({"nom":{"$ne":"aurelie"}}))
    return jsonify([serialize(r) for r in rows])

@app.route('/api/clients/<id>', methods=['PUT','DELETE'])
def api_edit(id):
    try: oid=ObjectId(id)
    except: return jsonify({'ok':False})
    if request.method=='DELETE': clients_col.delete_one({"_id":oid})
    else:
        d=request.json
        if 'bloque' in d: clients_col.update_one({"_id":oid},{"$set":{"bloque":int(bool(d['bloque']))}})
        if 'reset' in d: clients_col.update_one({"_id":oid},{"$set":{"pass":"1234","premiere":1}})
        if 'newpass' in d: clients_col.update_one({"_id":oid},{"$set":{"pass":d['newpass'],"premiere":0}})
        if 'nom' in d: clients_col.update_one({"_id":oid},{"$set":{"nom":d['nom'].lower(),"tel":d['tel'],"boutique":d['boutique']}})
    return jsonify({'ok':True})

@app.route('/api/stock')
def api_stock():
    b=request.args.get('boutique','')
    stock=[serialize(s) for s in stock_col.find({"boutique":b})]
    mouv=[serialize(m) for m in mouv_col.find({"boutique":b}).sort("_id",-1).limit(100)]
    return jsonify({'stock':stock,'mouvements':mouv})

@app.route('/api/stock', methods=['POST'])
def api_stock_save():
    d=request.json
    unite_base = d.get('unite_base') or d.get('unite') or 'bouteille'
    stock_base = float(d.get('stock_base') if d.get('stock_base') is not None else d.get('qte',0))
    achat_base = float(d.get('achat_base') if d.get('achat_base') is not None else d.get('achat',0))
    vente_base = float(d.get('vente_base') if d.get('vente_base') is not None else d.get('vente',0))
    emballages = d.get('emballages') or []
    groupe = d.get('groupe','Autre')
    nom = d.get('nom','')
    boutique = d.get('boutique','')
    data_to_set = {"groupe":groupe,"nom":nom,"boutique":boutique,"unite_base":unite_base,"stock_base":stock_base,"achat_base":achat_base,"vente_base":vente_base,"emballages":emballages,"qte":stock_base,"unite":unite_base,"achat":achat_base,"vente":vente_base,}
    if d.get('id') and len(str(d.get('id')))==24:
        try:
            oid=ObjectId(d['id'])
            stock_col.update_one({"_id":oid},{"$set":data_to_set})
            return jsonify({'ok':True})
        except: pass
    stock_col.update_one({"boutique":boutique,"nom":nom},{"$set":data_to_set},upsert=True)
    return jsonify({'ok':True})

@app.route('/api/stock/<id>', methods=['DELETE'])
def api_stock_del(id):
    try: stock_col.delete_one({"_id":ObjectId(id)})
    except: pass
    return jsonify({'ok':True})

@app.route('/api/mouvement', methods=['POST'])
def api_mouv():
    d=request.json
    try: row=stock_col.find_one({"_id":ObjectId(d['id'])})
    except: row=stock_col.find_one({"boutique":d['boutique'],"nom":d['produit']})
    if not row: return jsonify({'ok':False})
    qte_base = float(d['qte'])
    stock_actuel = float(row.get('stock_base', row.get('qte',0)))
    nq_base = stock_actuel - qte_base if d['type']=='Vendu' else stock_actuel + qte_base
    if nq_base<0: nq_base=0
    stock_col.update_one({"_id":row['_id']},{"$set":{"stock_base":nq_base, "qte":nq_base}})
    now=datetime.now()
    mouv_col.insert_one({"boutique":d['boutique'],"produit":d['produit'],"groupe":row.get('groupe'),"type":d['type'],"qte":qte_base,"qte_affichee": d.get('qte_affichee', f"{qte_base} {row.get('unite_base','')}"),"unite_cmd": d.get('unite_cmd',''),"facteur": d.get('facteur',1),"achat":row.get('achat_base', row.get('achat')),"vente":row.get('vente_base', row.get('vente')),"date":now.strftime('%Y-%m-%d'),"heure":now.strftime('%H:%M'),"datetime":now.isoformat()})
    return jsonify({'ok':True})

@app.route('/api/factures', methods=['GET','POST'])
def api_factures():
    if request.method == 'POST':
        d=request.json
        factures_col.insert_one({"boutique":d['boutique'],"num":d['num'],"client":d['client'],"tel":d['tel'],"total":d['total'],"produits":json.dumps(d['produits']),"date":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return jsonify({"ok":True})
    else:
        b=request.args.get('boutique')
        rows=[serialize(r) for r in factures_col.find({"boutique":b}).sort("_id",-1)]
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
        b=request.args.get('boutique')
        rows=[serialize(r) for r in depenses_col.find({"boutique":b}).sort("datetime",-1)]
        today=datetime.now().date()
        jour=[x for x in rows if x.get('date')==today.isoformat()]
        semaine=[x for x in rows if x.get('datetime') and datetime.fromisoformat(x['datetime']).date() >= today - timedelta(days=7)]
        mois=[x for x in rows if x.get('datetime') and datetime.fromisoformat(x['datetime']).date() >= today - timedelta(days=30)]
        return jsonify({"all":rows,"jour":jour,"semaine":semaine,"mois":mois,"total_jour":sum(x['montant'] for x in jour),"total_semaine":sum(x['montant'] for x in semaine),"total_mois":sum(x['montant'] for x in mois)})

@app.route('/api/depenses/<id>', methods=['DELETE'])
def del_dep(id):
    try: depenses_col.delete_one({"_id":ObjectId(id)})
    except: pass
    return jsonify({"ok":True})

@app.route('/api/dettes', methods=['GET','POST'])
def api_dettes():
    if request.method=='POST':
        d=request.json
        now=datetime.now()
        d['date_dette']=now.strftime("%d/%m/%Y %H:%M")
        d['datetime']=now.isoformat()
        d['statut']='paye' if float(d.get('reste',0))<=0 else 'en_cours'
        if 'paiements' not in d:
            d['paiements']=[]
            if float(d.get('deja_paye',0))>0:
                d['paiements'].append({"date":d['date_dette'],"montant":float(d['deja_paye'])})
        res=dettes_col.insert_one(d)
        return jsonify({"ok":True,"id":str(res.inserted_id)})
    else:
        b=request.args.get('boutique','')
        rows=[serialize(r) for r in dettes_col.find({"boutique":b}).sort("datetime",-1)]
        total_a_recup=sum(float(x.get('reste',0)) for x in rows if x.get('statut')!='paye')
        mois_str=datetime.now().strftime("%m/%Y")
        total_mois=0
        for r in rows:
            for p in r.get('paiements',[]):
                if mois_str in p.get('date',''):
                    total_mois+=float(p.get('montant',0))
        nb=len([x for x in rows if x.get('statut')!='paye'])
        return jsonify({"dettes":rows,"total_a_recup":total_a_recup,"total_recup_mois":total_mois,"nb":nb})

@app.route('/api/dettes/payer', methods=['POST'])
def api_dette_payer():
    d=request.json
    try: row=dettes_col.find_one({"_id":ObjectId(d['id'])})
    except: return jsonify({"ok":False})
    if not row: return jsonify({"ok":False})
    montant=float(d['montant'])
    new_reste=max(0,float(row.get('reste',0))-montant)
    new_paye=float(row.get('deja_paye',0))+montant
    statut='paye' if new_reste<=0 else 'en_cours'
    dettes_col.update_one({"_id":row['_id']},{"$set":{"reste":new_reste,"deja_paye":new_paye,"statut":statut},"$push":{"paiements":{"date":datetime.now().strftime("%d/%m/%Y %H:%M"),"montant":montant}}})
    return jsonify({"ok":True})

@app.route('/api/dettes/<id>', methods=['DELETE'])
def api_dette_del(id):
    try: dettes_col.delete_one({"_id":ObjectId(id)})
    except: pass
    return jsonify({"ok":True})

@app.route('/api/historique')
def api_histo():
    b=request.args.get('boutique','')
    all_mouv=[serialize(m) for m in mouv_col.find({"boutique":b}).sort("datetime",-1)]
    all_dep=[serialize(d) for d in depenses_col.find({"boutique":b}).sort("datetime",-1)]
    today=datetime.now().date()
    jour=[m for m in all_mouv if m.get('date')==today.isoformat()]
    semaine=[m for m in all_mouv if m.get('datetime') and datetime.fromisoformat(m['datetime']).date() >= today - timedelta(days=7)]
    dep_jour=[d for d in all_dep if d.get('date')==today.isoformat()]
    dep_semaine=[d for d in all_dep if d.get('datetime') and datetime.fromisoformat(d['datetime']).date() >= today - timedelta(days=7)]
    benef_jour = sum((x.get('vente',0)-x.get('achat',0))*x.get('qte',0) for x in jour if x['type']=='Vendu')
    benef_semaine = sum((x.get('vente',0)-x.get('achat',0))*x.get('qte',0) for x in semaine if x['type']=='Vendu')
    dep_jour_total = sum(x['montant'] for x in dep_jour)
    dep_semaine_total = sum(x['montant'] for x in dep_semaine)
    mois=[]
    for w in range(4):
        debut=today-timedelta(days=7*(w+1)); fin=debut+timedelta(days=6)
        items=[m for m in all_mouv if m.get('datetime') and debut <= datetime.fromisoformat(m['datetime']).date() <= fin]
        dep_items=[d for d in all_dep if d.get('datetime') and debut <= datetime.fromisoformat(d['datetime']).date() <= fin]
        if items or dep_items:
            benef = sum((x.get('vente',0)-x.get('achat',0))*x.get('qte',0) for x in items if x['type']=='Vendu')
            dep = sum(x['montant'] for x in dep_items)
            mois.append({"label": f"Semaine {4-w} : {debut.strftime('%d/%m')} - {fin.strftime('%d/%m')}", "items": items, "depenses": dep_items, "benef_brut": benef, "dep_total": dep, "benef_net": benef - dep})
    return jsonify({"jour":jour,"semaine":semaine,"mois":mois,"dep_jour":dep_jour,"dep_semaine":dep_semaine,"benef_jour_brut":benef_jour,"benef_jour_net":benef_jour - dep_jour_total,"benef_semaine_brut":benef_semaine,"benef_semaine_net":benef_semaine - dep_semaine_total,"dep_jour_total":dep_jour_total,"dep_semaine_total":dep_semaine_total})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
