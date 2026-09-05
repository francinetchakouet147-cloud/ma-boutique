<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Connexion</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#f8fafc;display:flex;align-items:center;justify-content:center;height:100vh}.card{border:0;border-radius:20px;box-shadow:0 8px 30px rgba(0,0,0,.08);width:100%;max-width:400px}</style></head><body>
<div class="card p-4">
<h4 class="fw-bold text-center">Boutique Aurélie</h4>
<p class="text-center text-muted small">Connexion Atlas</p>
<div id="alert" style="display:none" class="alert"></div>
<div id="loginBox">
<input id="nom" class="form-control mb-3" placeholder="Nom d'utilisateur (ex: bibi)" value="bibi">
<input id="pass" type="password" class="form-control mb-3" placeholder="Mot de passe">
<button class="btn btn-primary w-100 rounded-pill" onclick="login()">Se connecter</button>
</div>
<div id="newPassBox" style="display:none">
<p class="fw-bold text-warning">Première connexion : Crée ton nouveau mot de passe</p>
<input id="newpass" type="password" class="form-control mb-2" placeholder="Nouveau mot de passe">
<input id="newpass2" type="password" class="form-control mb-3" placeholder="Confirme">
<button class="btn btn-warning w-100 rounded-pill fw-bold" onclick="setNewPass()">Enregistrer et entrer</button>
</div>
</div>
<script>
let currentClient=null;
async function login(){
 let nom=document.getElementById('nom').value.trim().toLowerCase();
 let pass=document.getElementById('pass').value.trim();
 if(!nom||!pass){show('Remplis tout','danger');return;}
 let r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nom,pass})});
 let j=await r.json();
 if(!j.ok){show(j.msg||'Erreur','danger');return;}
 if(j.role=='admin'){localStorage.setItem('role','admin');location.href='/admin';return;}
 currentClient=j.client;
 if(j.premiere){
   document.getElementById('loginBox').style.display='none';
   document.getElementById('newPassBox').style.display='block';
   show('Première connexion, crée un nouveau mot de passe','warning');
 } else {
   localStorage.setItem('boutique', j.client.boutique);
   localStorage.setItem('client', JSON.stringify(j.client));
   location.href='/boutique';
 }
}
async function setNewPass(){
 let p1=document.getElementById('newpass').value.trim();
 let p2=document.getElementById('newpass2').value.trim();
 if(p1!=p2||p1.length<3){show('Mots de passe différents ou trop court','danger');return;}
 let r=await fetch('/api/clients/'+currentClient._id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({newpass:p1})});
 let j=await r.json();
 if(j.ok){
   localStorage.setItem('boutique', currentClient.boutique);
   localStorage.setItem('client', JSON.stringify(currentClient));
   location.href='/boutique';
 }
}
function show(m,type){let a=document.getElementById('alert');a.style.display='block';a.className='alert alert-'+type;a.innerText=m;}
</script></body></html>
