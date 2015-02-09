# rlim-logbook

rlim-logbook supports:
- addition of quotes: https://rlim-logbook.appspot.com/admin/addquote
- addition of wikipages: https://rlim-logbook.appspot.com/[page]
- addition of member(internal use): https://rlim-logbook.appspot.com/admin/signup [depricated]
- addition of internal wikipages: https://rlim-logbook.appspot.com/admin/internal/[page]
- flush the memcache:https://rlim-logbook.appspot.com/flush
- JSON API:
    - [Wikipages Json](/https://rlim-logbook.appspot.com/pages.json)
    - [Internalwikipages Json](/https://rlim-logbook.appspot.com/pages.json/admin/internal/pages.json)
    - [Quotes Json](/https://rlim-logbook.appspot.com/quotes.json)

Technology applied:
- Google Appengine (python) for web framework
- Bootstrap [flatly](http://bootswatch.com/flatly/) for styling
- Jinja2 for templating
- Icons [FontAwesome](http://fortawesome.github.io/Font-Awesome/)
- About template (CV) from [blacktie](http://www.blacktie.co/)

Hosted at: https://rlim-logbook.appspot.com/

TODO:
- admin html
- backup cronjob
