from backend.alert import notifier_email

bien_test = {
    "type": "Appartement",
    "surface": 45,
    "prix": 220000,
    "quartier": "Le Mourillon",
    "url_source": "https://www.seloger.com/annonces/achat/maison/toulon-83/trois-quartiers-siblas/267300099.htm?serp_view=list&search=distributionTypes%3DBuy%26estateTypes%3DHouse%2CApartment%26locations%3DAD08FR34378%26page%3D6#ln=classified_search_results&m=classified_search_results_classified_classified_detail_M",
    "description": "Nous avons trouvé un nouveau bien correspondant à votre recherche",
}

notifier_email("aurelie.rambout@gmail.com", [bien_test])

print("Email de test envoyé")