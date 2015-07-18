# fullstack_proj3

Project3 for Udacity Fullstack Web Developer Nanodegree

This code is based on the source provided in the Udacity Full Stack 
Foundations and Authentication & Authoriaztion courses.

This project uses python, the flask framework, an sqlite db 
and facebook and google 3rd party authentication API's to create a webapp to
display and update restaurant menus.  In order to make updates, users must 
first login and only the creator of a restaurant can make updates.

The json files containing the app ids to use with the 3rd party authentication
API's are not included so they will not work.

The following components must be installed to run: 
	python-psycopg2
	python-sqlalchemy
	python-pip
	werkzeug
	flask
	Flask-Login
	oauth2client
	requests
	httpllib2

From the python shell, run database_setup.py to create the database and 
lotsofmenus.py to populate some entries in the database.  Run
restaurantapp.py to start the web server and open "localhost:5000" from
a browser.

