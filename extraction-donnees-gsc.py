import streamlit as st
import pandas as pd
import datetime
import os
import pickle
import time
import io
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64

# Configuration de la page Streamlit
st.set_page_config(page_title="Extracteur de données Google Search Console", layout="wide")

# Styles CSS personnalisés
st.markdown("""
<style>
    .main-header {
        font-size: 26px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .sub-header {
        font-size: 18px;
        font-weight: bold;
        margin-top: 15px;
        margin-bottom: 10px;
    }
    .info-text {
        font-size: 14px;
        margin-bottom: 10px;
    }
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 24px;
        border-radius: 8px;
        border: none;
        font-size: 16px;
        font-weight: bold;
        transition-duration: 0.3s;
    }
    .stButton > button:hover {
        background-color: #45a049;
        box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
    }
    .download-link {
        display: inline-block;
        padding: 8px 16px;
        background-color: #3498db;
        color: white !important;
        text-decoration: none;
        border-radius: 5px;
        margin-top: 10px;
        font-weight: 500;
        text-align: center;
        transition: background-color 0.3s;
    }
    .download-link:hover {
        background-color: #2980b9;
        text-decoration: none;
    }
    div[data-baseweb="radio"] > div {
        margin-bottom: 8px;
        padding: 10px;
        border-radius: 5px;
        transition: background-color 0.2s;
    }
    div[data-baseweb="radio"] > div:hover {
        background-color: #f8f9fa;
    }
    /* Style pour les succès */
    .element-container .stSuccess {
        background-color: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #28a745;
    }
    /* Style pour les avertissements */
    .element-container .stWarning {
        background-color: #fff3cd;
        color: #856404;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #ffc107;
    }
    /* Style pour les erreurs */
    .element-container .stError {
        background-color: #f8d7da;
        color: #721c24;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #dc3545;
    }
    /* Style pour les messages d'accès refusé */
    .access-denied {
        background-color: #f8f9fa;
        border-left: 5px solid #6c757d;
        color: #495057;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        font-size: 14px;
    }
    .access-denied strong {
        color: #495057;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Titre de l'application
st.markdown('<div class="main-header">Extracteur de données Google Search Console</div>', unsafe_allow_html=True)

# Fonction d'authentification à l'API Google Search Console
def authenticate_gsc():
    SCOPES = ['https://www.googleapis.com/auth/webmasters']
    creds = None
    
    # Vérifier si nous sommes dans l'environnement Streamlit Cloud
    try:
        # Tenter d'accéder aux secrets Streamlit
        if 'token' in st.secrets:
            from google.oauth2.credentials import Credentials
            
            creds = Credentials(
                token=st.secrets.token.get('token', None),
                refresh_token=st.secrets.token.get('refresh_token', None),
                token_uri=st.secrets.token.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=st.secrets.credentials.get('client_id', None),
                client_secret=st.secrets.credentials.get('client_secret', None),
                scopes=SCOPES
            )
            
            st.success("Authentification via Streamlit Secrets réussie!")
            
    except Exception as e:
        # Utiliser la méthode locale si les secrets ne sont pas disponibles
        st.info("Utilisation de l'authentification locale.")
        
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
                
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    st.error("Le fichier credentials.json n'existe pas pour l'authentification locale.")
                    st.info("Veuillez configurer les secrets Streamlit ou fournir le fichier credentials.json.")
                    st.stop()
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=8080)
                
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
    
    # Si nous n'avons toujours pas de credentials valides
    if not creds:
        st.error("Impossible d'authentifier à l'API Google Search Console.")
        st.info("Veuillez configurer les secrets Streamlit ou utiliser l'application localement.")
        st.stop()
    
    service = build('searchconsole', 'v1', credentials=creds)
    return service

# Fonction pour récupérer les propriétés disponibles
def get_properties(service):
    site_list = service.sites().list().execute()
    properties = []
    
    if 'siteEntry' in site_list:
        for site in site_list['siteEntry']:
            properties.append(site['siteUrl'])
    
    return properties

# Fonction pour gérer les erreurs d'accès
def handle_access_error(error_message):
    if "User does not have sufficient permission for site" in error_message:
        property_name = error_message.split("'")[1] if "'" in error_message else "cette propriété"
        st.markdown(f"""
        <div class="access-denied">
            <strong>⚠️ Accès non autorisé</strong><br>
            Vous n'avez pas les droits suffisants pour accéder à la propriété <strong>{property_name}</strong>.<br>
            Vérifiez que cette propriété vous a bien été partagée avec les droits appropriés dans Google Search Console.
        </div>
        """, unsafe_allow_html=True)
        return True
    return False

# Fonction pour extraire les données par page avec contournement de la limite
def get_page_data(service, site_url, start_date, end_date):
    """
    Extrait les données de pages avec pagination pour dépasser la limite de 25000 URLs.
    Récupère toutes les données disponibles sans limite maximale.
    """
    all_results = []
    start_row = 0
    total_fetched = 0
    row_limit = 25000  # Valeur maximale fixe pour optimiser l'extraction
    
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    more_data = True
    while more_data:
        progress_text.info(f"Extraction des données par pages... ({total_fetched} lignes récupérées)")
        
        request = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['page'],
            'rowLimit': row_limit,
            'startRow': start_row
        }
        
        try:
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            if 'rows' not in response or not response['rows']:
                more_data = False
                break  # Pas plus de données à récupérer
            
            batch_size = len(response['rows'])
            for row in response['rows']:
                all_results.append({
                    'page': row['keys'][0],
                    'clicks': row['clicks'],
                    'impressions': row['impressions'],
                    'ctr': row['ctr'],
                    'position': row['position']
                })
            
            # Mise à jour pour la prochaine itération
            start_row += batch_size
            total_fetched += batch_size
            
            # Si nous avons reçu moins de lignes que demandées, nous avons fini
            if batch_size < row_limit:
                more_data = False
                
            # Mise à jour de la barre de progression (estimation basée sur le fait que nous recevons moins de données)
            progress_completion = 1.0 if not more_data else min(0.9, batch_size / row_limit)
            progress_bar.progress(progress_completion)
                
            # Pause pour éviter de dépasser les quotas d'API
            time.sleep(0.5)
            
        except Exception as e:
            error_message = str(e)
            if not handle_access_error(error_message):
                st.error(f"Erreur lors de l'extraction des données par pages : {e}")
            more_data = False
    
    progress_text.empty()
    progress_bar.empty()
    return pd.DataFrame(all_results)

# Fonction pour extraire les données par mot-clé avec contournement de la limite
def get_query_data(service, site_url, start_date, end_date):
    """
    Extrait les données de mots-clés avec pagination pour dépasser la limite de 25000.
    Récupère toutes les données disponibles sans limite maximale.
    """
    all_results = []
    start_row = 0
    total_fetched = 0
    row_limit = 25000  # Valeur maximale fixe pour optimiser l'extraction
    
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    more_data = True
    while more_data:
        progress_text.info(f"Extraction des données par mots-clés... ({total_fetched} lignes récupérées)")
        
        request = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['query'],
            'rowLimit': row_limit,
            'startRow': start_row
        }
        
        try:
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            if 'rows' not in response or not response['rows']:
                more_data = False
                break  # Pas plus de données à récupérer
            
            batch_size = len(response['rows'])
            for row in response['rows']:
                all_results.append({
                    'mot-clé': row['keys'][0],
                    'clicks': row['clicks'],
                    'impressions': row['impressions'],
                    'ctr': row['ctr'],
                    'position': row['position']
                })
            
            # Mise à jour pour la prochaine itération
            start_row += batch_size
            total_fetched += batch_size
            
            # Si nous avons reçu moins de lignes que demandées, nous avons fini
            if batch_size < row_limit:
                more_data = False
                
            # Mise à jour de la barre de progression (estimation basée sur le fait que nous recevons moins de données)
            progress_completion = 1.0 if not more_data else min(0.9, batch_size / row_limit)
            progress_bar.progress(progress_completion)
                
            # Pause pour éviter de dépasser les quotas d'API
            time.sleep(0.5)
            
        except Exception as e:
            error_message = str(e)
            if not handle_access_error(error_message):
                st.error(f"Erreur lors de l'extraction des données par mots-clés : {e}")
            more_data = False
    
    progress_text.empty()
    progress_bar.empty()
    return pd.DataFrame(all_results)

# Fonction pour extraire les données par page et mot-clé avec contournement de la limite
def get_page_query_data(service, site_url, start_date, end_date):
    """
    Extrait les données de pages et mots-clés avec pagination pour dépasser la limite de 25000.
    Récupère toutes les données disponibles sans limite maximale.
    """
    all_results = []
    start_row = 0
    total_fetched = 0
    row_limit = 25000  # Valeur maximale fixe pour optimiser l'extraction
    
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    more_data = True
    while more_data:
        progress_text.info(f"Extraction des données par pages et mots-clés... ({total_fetched} lignes récupérées)")
        
        request = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['page', 'query'],
            'rowLimit': row_limit,
            'startRow': start_row
        }
        
        try:
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            if 'rows' not in response or not response['rows']:
                more_data = False
                break  # Pas plus de données à récupérer
            
            batch_size = len(response['rows'])
            for row in response['rows']:
                all_results.append({
                    'page': row['keys'][0],
                    'mot-clé': row['keys'][1],
                    'clicks': row['clicks'],
                    'impressions': row['impressions'],
                    'ctr': row['ctr'],
                    'position': row['position']
                })
            
            # Mise à jour pour la prochaine itération
            start_row += batch_size
            total_fetched += batch_size
            
            # Si nous avons reçu moins de lignes que demandées, nous avons fini
            if batch_size < row_limit:
                more_data = False
                
            # Mise à jour de la barre de progression (estimation basée sur le fait que nous recevons moins de données)
            progress_completion = 1.0 if not more_data else min(0.9, batch_size / row_limit)
            progress_bar.progress(progress_completion)
                
            # Pause pour éviter de dépasser les quotas d'API
            time.sleep(0.5)
            
        except Exception as e:
            error_message = str(e)
            if not handle_access_error(error_message):
                st.error(f"Erreur lors de l'extraction des données par pages et mots-clés : {e}")
            more_data = False
    
    progress_text.empty()
    progress_bar.empty()
    return pd.DataFrame(all_results)

# Fonction pour générer un lien de téléchargement pour CSV
def get_download_link(df, filename, text):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" class="download-link">Télécharger {text}</a>'
    return href

# Fonction pour générer un lien de téléchargement pour Excel avec plusieurs onglets
def get_excel_download_link(dataframes, sheet_names, filename, text):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for df, sheet_name in zip(dataframes, sheet_names):
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    excel_data = output.getvalue()
    b64 = base64.b64encode(excel_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}" class="download-link" style="background-color: #2e7d32;">Télécharger {text}</a>'
    return href

# Fonction principale
def main():
    # Tentative d'authentification
    try:
        service = authenticate_gsc()
        
        # Récupération des propriétés
        properties = get_properties(service)
        
        if not properties:
            st.warning("Aucune propriété n'a été trouvée pour ce compte Google.")
            return
        
        # Sélection de la propriété
        selected_property = st.selectbox(
            "Sélectionnez une propriété",
            properties
        )
        
        # Sélection de la plage de dates
        st.markdown('<div class="sub-header">Sélectionnez la plage de dates</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "Date de début",
                value=datetime.date.today() - datetime.timedelta(days=30)
            )
        
        with col2:
            end_date = st.date_input(
                "Date de fin",
                value=datetime.date.today() - datetime.timedelta(days=1)
            )
        
        # Validation des dates
        if start_date > end_date:
            st.error("La date de début doit être antérieure à la date de fin.")
            return
        
        # Vérification si la plage de dates est trop grande
        if (end_date - start_date).days > 90:
            st.warning("Attention: Une plage de dates supérieure à 90 jours peut entraîner des temps d'extraction plus longs.")
        
        # Conversion des dates au format requis par l'API
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # Options d'extraction
        st.markdown('<div class="sub-header">Options d\'extraction</div>', unsafe_allow_html=True)
        
        extraction_type = st.radio(
            "Sélectionnez le type d'extraction :",
            ["Extraire les données par pages", 
             "Extraire les données par mots-clés", 
             "Extraire les données par pages et mots-clés",
             "Extraire les trois types de données"]
        )
        
        # Variables pour les options d'extraction
        extract_pages = extraction_type == "Extraire les données par pages" or extraction_type == "Extraire les trois types de données"
        extract_queries = extraction_type == "Extraire les données par mots-clés" or extraction_type == "Extraire les trois types de données"
        extract_pages_queries = extraction_type == "Extraire les données par pages et mots-clés" or extraction_type == "Extraire les trois types de données"
        
        # Bouton d'extraction avec style amélioré
        st.markdown("<br>", unsafe_allow_html=True)  # Espace avant le bouton
        extract_button = st.button("📊 Extraire les données")
        
        if extract_button:
            with st.spinner("Extraction des données en cours..."):
                # Création d'un conteneur pour afficher la progression
                progress_container = st.empty()
                
                # Extraction selon le type sélectionné
                if extraction_type == "Extraire les trois types de données":
                    # Créer un conteneur pour afficher la progression
                    progress_container.info("Extraction des trois types de données (avec pagination)...")
                    
                    # Extraction des pages
                    st.write("1. Extraction des données par pages...")
                    pages_df = get_page_data(service, selected_property, start_date_str, end_date_str)
                    if not pages_df.empty:
                        st.success(f"Extraction des données par pages réussie: {len(pages_df)} lignes.")
                        st.dataframe(pages_df.head(10))
                    else:
                        st.warning("Aucune donnée par page n'a été trouvée.")
                    
                    # Extraction des mots-clés
                    st.write("2. Extraction des données par mots-clés...")
                    queries_df = get_query_data(service, selected_property, start_date_str, end_date_str)
                    if not queries_df.empty:
                        st.success(f"Extraction des données par mots-clés réussie: {len(queries_df)} lignes.")
                        st.dataframe(queries_df.head(10))
                    else:
                        st.warning("Aucune donnée par mot-clé n'a été trouvée.")
                    
                    # Extraction des pages et mots-clés
                    st.write("3. Extraction des données par pages et mots-clés...")
                    pages_queries_df = get_page_query_data(service, selected_property, start_date_str, end_date_str)
                    if not pages_queries_df.empty:
                        st.success(f"Extraction des données par pages et mots-clés réussie: {len(pages_queries_df)} lignes.")
                        st.dataframe(pages_queries_df.head(10))
                    else:
                        st.warning("Aucune donnée par page et mot-clé n'a été trouvée.")
                    
                    # Proposer le téléchargement d'un fichier Excel avec les trois types de données
                    if not pages_df.empty or not queries_df.empty or not pages_queries_df.empty:
                        # Créer des dataframes vides pour les feuilles manquantes si nécessaire
                        if pages_df.empty:
                            pages_df = pd.DataFrame(columns=['page', 'clicks', 'impressions', 'ctr', 'position'])
                        if queries_df.empty:
                            queries_df = pd.DataFrame(columns=['mot-clé', 'clicks', 'impressions', 'ctr', 'position'])
                        if pages_queries_df.empty:
                            pages_queries_df = pd.DataFrame(columns=['page', 'mot-clé', 'clicks', 'impressions', 'ctr', 'position'])
                        
                        dataframes = [pages_df, queries_df, pages_queries_df]
                        sheet_names = ["Pages", "Mots-clés", "Pages et Mots-clés"]
                        
                        date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        excel_filename = f"gsc_data_{date_str}.xlsx"
                        
                        st.markdown(get_excel_download_link(dataframes, sheet_names, excel_filename, 
                                                          "le fichier Excel avec les trois types de données"), 
                                  unsafe_allow_html=True)
                        
                        # Proposer aussi le téléchargement des fichiers CSV individuels
                        st.write("Vous pouvez également télécharger chaque type de données séparément en CSV :")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if not pages_df.empty:
                                st.markdown(get_download_link(pages_df, "pages_data.csv", "les données par pages (CSV)"), 
                                          unsafe_allow_html=True)
                        with col2:
                            if not queries_df.empty:
                                st.markdown(get_download_link(queries_df, "queries_data.csv", "les données par mots-clés (CSV)"), 
                                          unsafe_allow_html=True)
                        with col3:
                            if not pages_queries_df.empty:
                                st.markdown(get_download_link(pages_queries_df, "pages_queries_data.csv", 
                                                           "les données par pages et mots-clés (CSV)"), 
                                          unsafe_allow_html=True)
                
                # Extraction des données par page
                elif extraction_type == "Extraire les données par pages":
                    progress_container.info("Extraction des données par pages (avec pagination)...")
                    pages_df = get_page_data(service, selected_property, start_date_str, end_date_str)
                    if not pages_df.empty:
                        st.success(f"Extraction des données par pages réussie: {len(pages_df)} lignes.")
                        st.dataframe(pages_df.head(10))
                        st.markdown(get_download_link(pages_df, "pages_data.csv", "les données par pages"), unsafe_allow_html=True)
                    else:
                        st.warning("Aucune donnée par page n'a été trouvée.")
                
                # Extraction des données par mot-clé
                elif extraction_type == "Extraire les données par mots-clés":
                    progress_container.info("Extraction des données par mots-clés (avec pagination)...")
                    queries_df = get_query_data(service, selected_property, start_date_str, end_date_str)
                    if not queries_df.empty:
                        st.success(f"Extraction des données par mots-clés réussie: {len(queries_df)} lignes.")
                        st.dataframe(queries_df.head(10))
                        st.markdown(get_download_link(queries_df, "queries_data.csv", "les données par mots-clés"), unsafe_allow_html=True)
                    else:
                        st.warning("Aucune donnée par mot-clé n'a été trouvée.")
                
                # Extraction des données par page et mot-clé
                elif extraction_type == "Extraire les données par pages et mots-clés":
                    progress_container.info("Extraction des données par pages et mots-clés (avec pagination)...")
                    pages_queries_df = get_page_query_data(service, selected_property, start_date_str, end_date_str)
                    if not pages_queries_df.empty:
                        st.success(f"Extraction des données par pages et mots-clés réussie: {len(pages_queries_df)} lignes.")
                        st.dataframe(pages_queries_df.head(10))
                        st.markdown(get_download_link(pages_queries_df, "pages_queries_data.csv", "les données par pages et mots-clés"), unsafe_allow_html=True)
                    else:
                        st.warning("Aucune donnée par page et mot-clé n'a été trouvée.")
                
                progress_container.empty()
                
    except Exception as e:
        error_message = str(e)
        if not handle_access_error(error_message):
            if "Address already in use" in error_message:
                st.markdown(f"""
                <div class="access-denied">
                    <strong>⚠️ Port déjà utilisé</strong><br>
                    Un autre programme utilise déjà le port nécessaire à l'authentification.<br>
                    Essayez de fermer d'autres instances de Streamlit ou redémarrez votre ordinateur.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"Une erreur s'est produite: {e}")
        
        st.info("Assurez-vous que vous avez correctement configuré les identifiants et que vous avez l'accès aux propriétés Google Search Console.")

if __name__ == "__main__":
    main()
