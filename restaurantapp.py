from flask import Flask, render_template, request, redirect,jsonify, url_for, flash


from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem, User
from flask import session as login_session
import random, string
import sqlalchemy.orm.exc

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

# This web app displays and manages restaurant and menu information using the python flask framework,
# sqlalchemy orm and 3rd party oauth2 providers for authentication.  Only the original creator of a
# restaurant can edit or delete information about it.

app = Flask(__name__)


# Lists use to display menu items
courses=['Appetizers', 'Entrees', 'Desserts', 'Beverages']
course=['Appetizer', 'Entree', 'Dessert', 'Beverage']

#Connect to Database and create database session
engine = create_engine('sqlite:///restaurantmenuwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Helper functions for creating and getting user information
def createUser(login):
    newUser = User(name=login['username'],email=login['email'],picture=login['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login['email']).one()
    return user.id

def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# Create anti-forgery state token to be included with all 3rd party authentication requests
@app.route('/login')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html',STATE=state)

# Logon using Facebook
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.2/me"
    # strip expire tag from access token
    token = result.split("&")[0]


    url = 'https://graph.facebook.com/v2.2/me?%s' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    # Handle case where facebook does not return an email
    if 'email' not in data:
        login_session['email']=data['name']+'@facebook.com'
    else:
        login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout, let's strip out the information before the equals sign in our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.2/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    #Check if user is in the database
    try:
        user = session.query(User).filter_by(email=login_session['email']).one()
    except sqlalchemy.orm.exc.NoResultFound:
        createUser(login_session)

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output

# Logoff using Facebook
@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    print facebook_id
    print access_token
    url = 'https://graph.facebook.com/%s%s/permissions' % (facebook_id,access_token)
    print url
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return  True

#Logon using Google
CLIENT_ID = json.loads(open('client_secrets.json','r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu"

@app.route('/gconnect',methods=['POST'])
def gconnect():
    #validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'),401)
        response.header['Content-Type'] = 'application/json'
        return response
    # obtain authorization code
    code = request.data

    try:
        #Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code.'),401)
        response.headers['Content-Type'] = 'application/json'
        return response

    #Check that the access token is valid
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'%access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')),500)
        response.headers['Content-Type'] = 'application/json'
        
    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps("Token's user ID doesn't match given user ID."),401)
        response.header['Content-Type'] = 'application/json'
        return response
    
    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps("Token's client ID doesn't match app's."),401)
        response.header['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),200)
        response.headers['Content-Type'] = 'application/json'
        return response
    
    #Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    #Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt' : 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    #Check if user is in the database
    try:
        user = session.query(User).filter_by(email=login_session['email']).one()
    except sqlalchemy.orm.exc.NoResultFound:
        createUser(login_session)
        
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style="width: 300px;border-radius: 150px;-webkit-border-radius: 150px;-mod-border-radius: 150px;">'
    flash('You are now logged in as %s' % login_session['username'])
    print "done!"
    return output

#Logoff using Google
@app.route('/gdisconnect')
def gdisconnect():
    #Only disconnect a connected user
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(json.dumps('Current user not connected.'),401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        return True
    else:
        # invalid token
        return False
    
# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            success=gdisconnect()
	    if success:
            	del login_session['gplus_id']
            	del login_session['credentials']
        if login_session['provider'] == 'facebook':
            success=fbdisconnect()
	    if success:
            	del login_session['facebook_id']
	if success:
		username=login_session['username']
        	del login_session['username']
        	del login_session['email']
        	del login_session['picture']
        	del login_session['provider']
        	flash('Successfully disconnected %s' % username)
	else:
		flash('Unable to disconnect %s'% login_session['username'])
        return redirect(url_for('showRestaurants'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showRestaurants'))

#JSON APIs to view Restaurant Information
@app.route('/restaurant/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    try:
        restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
        items = session.query(MenuItem).filter_by(restaurant_id = restaurant_id).all()
        return jsonify(MenuItems=[i.serialize for i in items])
    except sqlalchemy.orm.exc.NoResultFound:
        response = make_response(json.dumps("Invalid restaurant id"),500)
        response.headers['Content-Type'] = 'application/json'
        return response

@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(restaurant_id, menu_id):
    try:
        Menu_Item = session.query(MenuItem).filter_by(id = menu_id, restaurant_id=restaurant_id).one()
        return jsonify(Menu_Item = Menu_Item.serialize)
    except sqlalchemy.orm.exc.NoResultFound:
        response = make_response(json.dumps("Invalid restaurant or menu id"),500)
        response.headers['Content-Type'] = 'application/json'
        return response

@app.route('/restaurant/JSON')
def restaurantsJSON():
    restaurants = session.query(Restaurant).all()
    return jsonify(restaurants= [r.serialize for r in restaurants])
           
#Show all restaurants
@app.route('/')
@app.route('/restaurant/')
def showRestaurants():
  restaurants = session.query(Restaurant).order_by(asc(Restaurant.name))
  if 'email' in login_session:
      return render_template('restaurants.html', restaurants=restaurants,logged_in=True)
  else:
      return render_template('publicrestaurants.html', restaurants=restaurants, logged_in=False)

#Create a new restaurant
@app.route('/restaurant/new/', methods=['GET','POST'])
def newRestaurant():
  # If not logged in, redirect to login screen. Prevents someone from accessing page directly
  # without logging in
  if 'email' not in login_session:
      return redirect(url_for('login'))
  if request.method == 'POST':
      if 'submit' in request.form and request.form['name']:
          try:
            checkRestaurant = session.query(Restaurant).filter_by(name=request.form['name']).one()
            flash('Restaurant %s Already Exists' % request.form['name'])
          except:
            newRestaurant = Restaurant(name = request.form['name'],user_id=getUserID(login_session['email']))
            session.add(newRestaurant)
            session.commit()
            flash('New Restaurant %s successfully created' % newRestaurant.name)
                
      return redirect(url_for('showRestaurants'))
  else:
      return render_template('newRestaurant.html',logged_in=True)

#Edit a restaurant name
@app.route('/restaurant/<int:restaurant_id>/edit/', methods = ['GET', 'POST'])
def editRestaurant(restaurant_id):
  if 'email' not in login_session:
      return redirect(url_for('login'))
  editedRestaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
  user=getUserInfo(editedRestaurant.user_id)
  if login_session['email'] != user.email:
      flash('Only %s can modify this restaurant'%user.name)
      return redirect(url_for('showRestaurants'))
  if request.method == 'POST':
      if 'submit' in request.form and request.form['name']:
          checkRestaurant = session.query(Restaurant).filter_by(name=request.form['name']).all()
          if len(checkRestaurant) > 0:
                 flash('Restaurant %s Already Exists' % request.form['name'])
                 return render_template('editRestaurant.html', restaurant = editedRestaurant)
          else:
            oldname=editedRestaurant.name
            editedRestaurant.name = request.form['name']
            session.add(editedRestaurant)
            session.commit()
            flash('Restaurant %s successfully renamed to %s' % (oldname,editedRestaurant.name))
      return redirect(url_for('showMenu', restaurant_id = restaurant_id))
  else:
    return render_template('editRestaurant.html', restaurant = editedRestaurant,logged_in=True)


#Delete a restaurant
@app.route('/restaurant/<int:restaurant_id>/delete/', methods = ['GET','POST'])
def deleteRestaurant(restaurant_id):
  if 'email' not in login_session:
      return redirect(url_for('login'))
  restaurantToDelete = session.query(Restaurant).filter_by(id = restaurant_id).one()
  user=getUserInfo(restaurantToDelete.user_id)
  if login_session['email'] != user.email:
      flash('Only %s can delete this restaurant'%user.name)
      return redirect(url_for('showMenu',restaurant_id=restaurant_id))
  if request.method == 'POST':
      if 'submit' in request.form:
        session.delete(restaurantToDelete)
        flash('%s Successfully Deleted' % restaurantToDelete.name)
        session.commit()
      return redirect(url_for('showRestaurants', restaurant_id = restaurant_id))
  else:
    return render_template('deleteRestaurant.html',restaurant = restaurantToDelete,logged_in=True)

#Show a restaurant menu
@app.route('/restaurant/<int:restaurant_id>/')
@app.route('/restaurant/<int:restaurant_id>/menu/')
def showMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one() 
    items=[[] for i in range(len(courses))]
    for i, c in enumerate(course):
        items[i] = session.query(MenuItem).filter_by(restaurant_id = restaurant_id,course=c).all()
    user = getUserInfo(restaurant.user_id)
    logged_in=False
    if 'email' in login_session:
        logged_in=True
    if logged_in and getUserID(login_session['email']) == restaurant.user_id:
        return render_template('menu.html', items = items, restaurant = restaurant,course_headers=courses,numcourses=len(courses),logged_in=logged_in)
    else:
        return render_template('publicmenu.html', items = items, restaurant = restaurant,course_headers=courses,numcourses=len(courses),logged_in=logged_in,creator=user)
     
#Create a new menu item
@app.route('/restaurant/<int:restaurant_id>/menu/new/',methods=['GET','POST'])
def newMenuItem(restaurant_id):
  if 'email' not in login_session:
      return redirect(url_for('login'))
  restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
  user=getUserInfo(restaurant.user_id)
  if login_session['email'] != user.email:
      flash('Only %s can add a menu item to this restaurant'%user.name)
      return redirect(url_for('showRestaurants'))
  if request.method == 'POST':
      if 'submit'in request.form:
          if request.form['name'] and request.form['price'] and 'course' in request.form:
              newItem = MenuItem(name = request.form['name'], description = request.form['description'],
                                 price = request.form['price'], course = request.form['course'],
                                 restaurant_id = restaurant_id, user_id=restaurant.user_id)
              session.add(newItem)
              session.commit()
              flash('New menu item, %s, successfully created' % (newItem.name))
          else:
              flash('Name, Price, and Course fields are required')
              return render_template('newmenuitem.html', restauran_id=restaurant_id,course=course)
      return redirect(url_for('showMenu', restaurant_id = restaurant_id))
  else:
      return render_template('newmenuitem.html', restaurant_id = restaurant_id, course=course,logged_in=True)

#Edit a menu item
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit', methods=['GET','POST'])
def editMenuItem(restaurant_id, menu_id):
    if 'email' not in login_session:
        return redirect(url_for('login'))
    editedItem = session.query(MenuItem).filter_by(id = menu_id).one()
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    user=getUserInfo(restaurant.user_id)
    if login_session['email'] != user.email:
      flash('Only %s can edit this menu item'%user.name)
      return redirect(url_for('showRestaurants'))
    if request.method == 'POST':
        if 'submit' in request.form:
            oldname=editedItem.name
            if request.form['name']:
                editedItem.name = request.form['name']
            if request.form['description']:
                editedItem.description = request.form['description']
            if request.form['price']:
                editedItem.price = request.form['price']
            editedItem.course = request.form['course']
            session.add(editedItem)
            session.commit() 
            flash('Menu item, %s, successfully edited' % oldname)
        return redirect(url_for('showMenu', restaurant_id = restaurant_id))
    else:
        return render_template('editmenuitem.html', restaurant_id = restaurant_id, menu_id = menu_id, item = editedItem,logged_in=True)


#Delete a menu item
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/delete', methods = ['GET','POST'])
def deleteMenuItem(restaurant_id,menu_id):
    if 'email' not in login_session:
      return redirect(url_for('login'))
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    itemToDelete = session.query(MenuItem).filter_by(id = menu_id).one()
    user=getUserInfo(restaurant.user_id)
    if login_session['email'] != user.email:
      flash('Only %s can delete this item'%user.name)
      return redirect(url_for('showRestaurants'))
    if request.method == 'POST':
        if 'submit' in request.form:
            session.delete(itemToDelete)
            session.commit()
            flash('Menu item, %s, successfully deleted' % itemToDelete.name)
        return redirect(url_for('showMenu', restaurant_id = restaurant_id))
    else:
        return render_template('deleteMenuItem.html', item = itemToDelete,logged_in=True)




if __name__ == '__main__':
  app.secret_key = 'super_secret_key'
  app.debug = True
  app.run(host = '0.0.0.0', port = 5000)
