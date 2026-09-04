from flask import Flask, render_template, request, jsonify
import sqlite3, os, json
from datetime import datetime, timedelta

app = Flask(__name__)
DB='stock.db'

def db():
    con=sqlite3.connect(DB)
    con.row_factory=sqlite3.Row
    return con

def init_db():
    con=db(); c=con.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY, nom TEXT UNIQUE, tel TEXT, boutique TEXT, pass TEXT, premiere INTEGER DEFAULT 1, bloque INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stock (id INTEGER PRIMARY KEY, boutique TEXT, groupe TEXT, nom TEXT, qte REAL, unite TEXT, achat REAL, vente REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS mouvements (id INTEGER PRIMARY KEY, boutique TEXT, produit TEXT, groupe TEXT, type TEXT, qte REAL, achat REAL, vente REAL, date TEXT, heure TEXT, datetime TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS factures (id INTEGER PRIMARY KEY, boutique TEXT, num TEXT, client TEXT, tel TEXT, total INTEGER, produits TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS depenses (id INTEGER PRIMARY KEY, boutique TEXT, motif TEXT, categorie TEXT, montant REAL, date TEXT, heure TEXT, datetime TEXT)''')
    try: c.execute('ALTER TABLE mouvements ADD COLUMN groupe TEXT')
    except: pass
    try: c.execute('ALTER TABLE mouvements ADD COLUMN achat REAL')
    except: pass
    try: c.execute('ALTER TABLE mouvements ADD COLUMN vente REAL')
    except: pass
    try: c.execute('ALTER TABLE mouvements ADD COLUMN heure TEXT')
    except: pass
    try: c.execute('ALTER TABLE mouvements ADD COLUMN datetime TEXT')
    except: pass
    c.execute('SELECT * FROM clients WHERE nom="aurelie"')
    if not c.fetchone():
        c.execute('INSERT INTO clients (nom,tel,boutique,pass,premiere) VALUES (?,?,?,?,?)',('aurelie','000','Admin','aurelie123',0))
    con.commit(); con.close()

# On initialise la base au démarrage pour Render
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
    con=db(); c=con.cursor(); c.execute('SELECT * FROM clients WHERE nom=?', (nom,)); cl=c.fetchone(); con.close()
    if not cl: return jsonify({'ok':False,'msg':'Client inconnu'})
    if cl['bloque']: return jsonify({'ok':False,'msg':'Compte bloqué'})
    if cl['pass']!=pas: return jsonify({'ok':False,'msg':'Mauvais mot de passe'})
    return jsonify({'ok':True,'role':'client','premiere':bool(cl['premiere']),'client':dict(cl)})

@app.route('/api/clients')
def api_clients():
    con=db(); rows=con.execute('SELECT * FROM clients WHERE nom!="aurelie"').fetchall(); con.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/clients', methods=['POST'])
def api_add():
    d=request.json; con=db()
    try: con.execute('INSERT INTO clients (nom,tel,boutique,pass,premiere) VALUES (?,?,?,?,1)', (d['nom'].lower(),d['tel'],d['boutique'],'1234')); con.commit()
    except: return jsonify({'ok':False,'msg':'Nom déjà utilisé'})
    con.close(); return jsonify({'ok':True})

@app.route('/api/clients/<int:id>', methods=['PUT','DELETE'])
def api_edit(id):
    con=db(); c=con.cursor()
    if request.method=='DELETE': c.execute('DELETE FROM clients WHERE id=?',(id,))
    else:
        d=request.json
        if 'bloque' in d: c.execute('UPDATE clients SET bloque=? WHERE id=?',(int(d['bloque']),id))
        if 'reset' in d: c.execute('UPDATE clients SET pass="1234", premiere=1 WHERE id=?',(id,))
        if 'newpass' in d: c.execute('UPDATE clients SET pass=?, premiere=0 WHERE id=?',(d['newpass'],id))
        if 'nom' in d: c.execute('UPDATE clients SET nom=?, tel=?, boutique=? WHERE id=?',(d['nom'],d['tel'],d['boutique'],id))
    con.commit(); con.close(); return jsonify({'ok':True})

@app.route('/api/stock')
def api_stock():
    b=request.args.get('boutique',''); con=db()
    stock=[dict(r) for r in con.execute('SELECT * FROM stock WHERE boutique=?',(b,)).fetchall()]
    mouv=[dict(r) for r in con.execute('SELECT * FROM mouvements WHERE boutique=? ORDER BY id DESC',(b,)).fetchall()]
    con.close(); return jsonify({'stock':stock,'mouvements':mouv})

@app.route('/api/stock', methods=['POST'])
def api_stock_save():
    d=request.json; con=db(); c=con.cursor()
    if d.get('id'): c.execute('UPDATE stock SET groupe=?, nom=?, qte=?, unite=?, achat=?, vente=? WHERE id=?',(d['groupe'],d['nom'],d['qte'],d['unite'],d['achat'],d['vente'],d['id']))
    else: c.execute('INSERT INTO stock (boutique,groupe,nom,qte,unite,achat,vente) VALUES (?,?,?,?,?,?,?)',(d['boutique'],d['groupe'],d['nom'],d['qte'],d['unite'],d['achat'],d['vente']))
    con.commit(); con.close(); return jsonify({'ok':True})

@app.route('/api/stock/<int:id>', methods=['DELETE'])
def api_stock_del(id): con=db(); con.execute('DELETE FROM stock WHERE id=?',(id,)); con.commit(); con.close(); return jsonify({'ok':True})

@app.route('/api/mouvement', methods=['POST'])
def api_mouv():
    d=request.json; con=db(); c=con.cursor()
    row=c.execute('SELECT * FROM stock WHERE id=?',(d['id'],)).fetchone()
    if not row: return jsonify({'ok':False})
    nq=row['qte']-float(d['qte']) if d['type']=='Vendu' else row['qte']+float(d['qte'])
    if nq<0: nq=0
    c.execute('UPDATE stock SET qte=? WHERE id=?',(nq,d['id']))
    now=datetime.now()
    c.execute('INSERT INTO mouvements (boutique,produit,groupe,type,qte,achat,vente,date,heure,datetime) VALUES (?,?,?,?,?,?,?,?,?,?)',
              (d['boutique'],d['produit'],row['groupe'],d['type'],d['qte'],row['achat'],row['vente'],now.strftime('%Y-%m-%d'),now.strftime('%H:%M'),now.isoformat()))
    con.commit(); con.close(); return jsonify({'ok':True})

@app.route('/api/factures', methods=['GET','POST'])
def api_factures():
    con=db(); c=con.cursor()
    if request.method == 'POST':
        d=request.json
        c.execute("INSERT INTO factures (boutique,num,client,tel,total,produits,date) VALUES (?,?,?,?,?,?,?)",
                  (d['boutique'],d['num'],d['client'],d['tel'],d['total'],json.dumps(d['produits']), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        con.commit(); con.close()
        return jsonify({"ok":True})
    else:
        b=request.args.get('boutique')
        rows=[dict(r) for r in con.execute("SELECT * FROM factures WHERE boutique=? ORDER BY id DESC", (b,)).fetchall()]
        con.close()
        return jsonify(rows)

@app.route('/api/facture/<int:id>', methods=['DELETE'])
def del_facture(id):
    con=db(); con.execute("DELETE FROM factures WHERE id=?", (id,)); con.commit(); con.close()
    return jsonify({"ok":True})

@app.route('/api/depenses', methods=['GET','POST'])
def api_depenses():
    con=db(); c=con.cursor()
    if request.method == 'POST':
        d=request.json; now=datetime.now()
        c.execute("INSERT INTO depenses (boutique,motif,categorie,montant,date,heure,datetime) VALUES (?,?,?,?,?,?,?)",
                  (d['boutique'],d['motif'],d['categorie'],d['montant'],now.strftime('%Y-%m-%d'),now.strftime('%H:%M'),now.isoformat()))
        con.commit(); con.close()
        return jsonify({"ok":True})
    else:
        b=request.args.get('boutique')
        rows=[dict(r) for r in con.execute("SELECT * FROM depenses WHERE boutique=? ORDER BY datetime DESC",(b,)).fetchall()]
        con.close()
        today=datetime.now().date()
        jour=[x for x in rows if x['date']==today.isoformat()]
        semaine=[x for x in rows if datetime.fromisoformat(x['datetime']).date() >= today - timedelta(days=7)]
        mois=[x for x in rows if datetime.fromisoformat(x['datetime']).date() >= today - timedelta(days=30)]
        return jsonify({"all":rows, "jour":jour, "semaine":semaine, "mois":mois,
                        "total_jour":sum(x['montant'] for x in jour),
                        "total_semaine":sum(x['montant'] for x in semaine),
                        "total_mois":sum(x['montant'] for x in mois)})

@app.route('/api/depenses/<int:id>', methods=['DELETE'])
def del_dep(id):
    con=db(); con.execute("DELETE FROM depenses WHERE id=?",(id,)); con.commit(); con.close()
    return jsonify({"ok":True})

@app.route('/api/historique')
def api_histo():
    b=request.args.get('boutique',''); con=db()
    all_mouv=[dict(r) for r in con.execute('SELECT * FROM mouvements WHERE boutique=? ORDER BY datetime DESC',(b,)).fetchall()]
    has_dep = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='depenses'").fetchone()
    all_dep=[dict(r) for r in con.execute('SELECT * FROM depenses WHERE boutique=? ORDER BY datetime DESC',(b,)).fetchall()] if has_dep else []
    con.close()
    today=datetime.now().date()
    jour=[m for m in all_mouv if m['date']==today.isoformat()]
    semaine=[]
    for i in range(1,8):
        d=(today-timedelta(days=i)).isoformat()
        semaine.extend([m for m in all_mouv if m['date']==d])
    dep_jour=[d for d in all_dep if d['date']==today.isoformat()]
    dep_semaine=[d for d in all_dep if datetime.fromisoformat(d['datetime']).date() >= today - timedelta(days=7)]
    benef_jour = sum((x['vente']-x['achat'])*x['qte'] for x in jour if x['type']=='Vendu')
    benef_semaine = sum((x['vente']-x['achat'])*x['qte'] for x in semaine if x['type']=='Vendu')
    dep_jour_total = sum(x['montant'] for x in dep_jour)
    dep_semaine_total = sum(x['montant'] for x in dep_semaine)
    mois=[]
    for w in range(4):
        debut=today-timedelta(days=7*(w+2)+1); fin=debut+timedelta(days=6)
        items=[m for m in all_mouv if debut.isoformat() <= m['date'] <= fin.isoformat()]
        dep_items=[d for d in all_dep if debut.isoformat() <= d['date'] <= fin.isoformat()]
        if items or dep_items:
            benef = sum((x['vente']-x['achat'])*x['qte'] for x in items if x['type']=='Vendu')
            dep = sum(x['montant'] for x in dep_items)
            mois.append({"label": f"Semaine {4-w} : {debut.strftime('%d/%m')} - {fin.strftime('%d/%m')}", "vendu": sum(x['qte'] for x in items if x['type']=='Vendu'), "recharge": sum(x['qte'] for x in items if x['type']=='Rechargé'), "items": items, "depenses": dep_items, "benef_brut": benef, "dep_total": dep, "benef_net": benef - dep})
    return jsonify({"jour":jour,"semaine":semaine,"mois":mois,"all":all_mouv,"dep_jour":dep_jour,"dep_semaine":dep_semaine,"benef_jour_brut":benef_jour,"benef_jour_net":benef_jour - dep_jour_total,"benef_semaine_brut":benef_semaine,"benef_semaine_net":benef_semaine - dep_semaine_total,"dep_jour_total":dep_jour_total,"dep_semaine_total":dep_semaine_total})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)