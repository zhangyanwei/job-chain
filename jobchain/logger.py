import logging.config

config = {
    'disable_existing_loggers': False,
    'version': 1,
    'formatters': {
        'short': {
            'format': '%(asctime)s %(levelname)s [%(module)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'formatter': 'short',
            'class': 'logging.StreamHandler'
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO'
        },
        'jenkins': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        }
    },
}


logging.config.dictConfig(config)
logger = logging.getLogger('jenkins')
