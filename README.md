# fullstack_proj3

Project3 for Udacity Fullstack Web Developer Nanodegree

This code is based on the source provided in the Udacity Full Stack 
Foundations and Authentication & Authoriaztion courses.

This project uses python, the flask framework, an sqlite db 
and facebook and google 3rd party authentication API's to create a webapp to
display and update restaurant menus.  In order to make updates, users must 
first login and only the creator of a restaurant can make updates.

The json files containing the app ids to use with the 3rd party authentication
API's are not included so they will not work. To obtain these credentials, go 
to the following websites and create a new project.  If you don't already have
a google or facebook account you'll need to create one.

https://developers.google.com/project
https://developers.facebook.com/apps

Follow the instructions to get a client/app id and secret key.  For google,
select the download json button.  Put the downloaded file in the same 
directory as the restaurantapp.py file and rename it client_secrets.json.
For facebook, copy the app id and secret into the fb_client_secrets.json file
replacing "ID HERE" and "SECRET HERE"


The following components must be installed to run: 
	python-psycopg2==2.4.5
	python-sqlalchemy==0.8.4
	werkzeug=0.8.3
	flask==0.9
	Flask-Login==0.1.3
	oauth2client==1.4.11
	requests==2.2.1
	httpllib2==0.9.1

From the python shell, run database_setup.py to create the database and 
lotsofmenus.py to populate some entries in the database.  Run
restaurantapp.py to start the web server and open "localhost:5000" from
a browser.

