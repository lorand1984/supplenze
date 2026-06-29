import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chiave-segreta-di-default-per-sviluppo'

    # Abilita il debug mode (ricarica automatica del server)
    DEBUG = True

    # Ricarica i template quando vengono modificati (senza riavviare il server)
    TEMPLATES_AUTO_RELOAD = True

    # Disabilita la cache dei file statici (utile in sviluppo)
    SEND_FILE_MAX_AGE_DEFAULT = 0