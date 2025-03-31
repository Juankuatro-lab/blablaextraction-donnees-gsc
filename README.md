# Extracteur de données Google Search Console

## Description

Une application Streamlit puissante pour extraire et analyser les données de performance de votre site web directement depuis Google Search Console.

## Fonctionnalités principales

🔍 **Types d'extraction de données**
- Extraction par pages
- Extraction par mots-clés
- Extraction combinée pages et mots-clés
- Option d'extraction de tous les types de données

📊 **Caractéristiques clés**
- Interface utilisateur intuitive
- Pagination automatique pour contourner les limites de l'API
- Téléchargement en CSV et Excel
- Extraction de données sur une période personnalisable

## Prérequis

- Python 3.7+
- Compte Google Search Console
- Identifiants d'API Google

## Installation

1. Clonez le dépôt :
```bash
git clone https://github.com/votre-utilisateur/gsc-extractor.git
cd gsc-extractor
```

2. Créez un environnement virtuel (recommandé) :
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
```

3. Installez les dépendances :
```bash
pip install -r requirements.txt
```

## Configuration

### Authentification Google

1. Créez un projet dans la Console Google Cloud
2. Activez l'API Google Search Console
3. Générez des identifiants OAuth 2.0
4. Téléchargez le fichier `credentials.json`

### Options de configuration

- Pour un déploiement local : placez `credentials.json` dans le dossier du projet
- Pour Streamlit Cloud : configurez les secrets avec vos identifiants

## Utilisation

### Lancement de l'application

```bash
streamlit run gsc_extractor.py
```

### Workflow d'extraction

1. Sélectionnez une propriété Google Search Console
2. Choisissez une plage de dates
3. Sélectionnez le type d'extraction
4. Cliquez sur "Extraire les données"

## Types d'extraction

### 1. Données par pages
- URL de la page
- Nombre de clics
- Impressions
- Taux de clic (CTR)
- Position moyenne

### 2. Données par mots-clés
- Mots-clés recherchés
- Nombre de clics
- Impressions
- Taux de clic (CTR)
- Position moyenne

### 3. Données par pages et mots-clés
- URL de la page
- Mots-clés spécifiques à la page
- Clics
- Impressions
- Taux de clic (CTR)
- Position moyenne

## Formats de sortie

- CSV pour chaque type de données
- Fichier Excel multi-onglets avec tous les types de données

## Limitations

- Extraction limitée à 90 jours de données
- Dépend des autorisations de votre compte Google Search Console

## Dépannage

- Vérifiez vos autorisations dans Google Search Console
- Assurez-vous que le fichier `credentials.json` est correct
- En cas d'erreurs, consultez la documentation de l'API Google

## Contribution

Les contributions sont les bienvenues ! Veuillez :
- Forker le dépôt
- Créer une branche pour votre fonctionnalité
- Soumettre une pull request

## Licence

[Spécifiez votre licence]

## Avertissement

Cette application n'est pas officiellement liée à Google. Elle utilise l'API Google Search Console sous réserve des conditions de service de Google.

## Contact

[Vos informations de contact ou lien vers le dépôt GitHub]
