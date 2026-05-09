# 🏦 NeaBank — Application Bancaire de Simulation

Une Neo-Bank complète avec authentification, dashboard client, panel admin et gestion en temps réel.

## 🚀 Lancement Rapide

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Lancer l'application
python app.py
```

Ouvrir : **http://localhost:5000**

---

## 🔐 Accès Admin

| Champ | Valeur |
|-------|--------|
| Email | `admin@neobank.io` |
| Mot de passe | `admin1234` |
| URL | `/admin` |

---

## 📁 Arborescence

```
neobank/
├── app.py                    # Backend Flask principal
├── requirements.txt          # Dépendances Python
├── instance/
│   └── neobank.db           # Base de données SQLite (auto-créée)
└── templates/
    ├── index.html           # Landing page + formulaire auth
    ├── dashboard.html       # Dashboard client (SPA)
    ├── admin.html           # Panel administrateur
    └── suspended.html       # Page compte suspendu
```

---

## ✨ Fonctionnalités

### Côté Client
- ✅ Inscription / Connexion sécurisée
- ✅ Dashboard temps réel (Fetch API, auto-refresh 10s)
- ✅ Solde animé, historique des transactions
- ✅ Carte bancaire visuelle avec numéro masquable
- ✅ Activation carte virtuelle
- ✅ Virement par IBAN (interne et externe simulé)
- ✅ Notifications en temps réel
- ✅ Génération automatique IBAN + numéro de carte

### Côté Admin
- ✅ Vue d'ensemble (stats globales)
- ✅ Liste complète des utilisateurs
- ✅ Modification du solde instantanée
- ✅ Envoi de notifications personnalisées
- ✅ Suspension / Réactivation de compte
- ✅ Redirection instantanée si compte suspendu

### Technique
- ✅ Flask + SQLite (persistance totale)
- ✅ Hachage des mots de passe (Werkzeug)
- ✅ Sessions sécurisées côté serveur
- ✅ API REST JSON
- ✅ Design Dark Mode (Syne + DM Sans + Tailwind)
