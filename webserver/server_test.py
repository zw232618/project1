
#this is custom server
import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response
from flask import flash, session, abort

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = "super secret key"


DB_USER = "yf2486"
DB_PASSWORD = "2atj5yd7"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"

#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request
  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#custom routers


@app.route('/')
def home():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        return render_template('home.html')


@app.route('/login', methods=['POST'])
def do_admin_login():
    cursor = g.conn.execute("SELECT user_id FROM users")
    user_ids = []
    for p in cursor:
    	
        user_ids.append(str(p['user_id']))
    cursor.close()

    if  request.form['user_id'] in user_ids:
        session['logged_in'] = True
        session['user_id'] = int(request.form['user_id'])
    else:
        flash('There is no such user')
    return home()

@app.route("/logout")
def logout():
    session['logged_in'] = False
    session['user_id'] = 0
    return redirect('/')

@app.route("/all_paintings")
def all_paintings():
    cursor = g.conn.execute("SELECT name FROM painting_stored_included")
    painting_names = []
    for p in cursor:
        painting_names.append(p['name'])
    cursor.close()

    context = dict(paintings = painting_names)
    return render_template('all_paintings.html', **context)

@app.route("/painting",methods=['POST'])
def painting():
    cursor = g.conn.execute("SELECT name FROM painting_stored_included")
    painting_names = []
    for p in cursor:
    	print(p['name'])
        painting_names.append(p['name'])
    cursor.close()	

    painting_name = request.form['painting']
    if painting_name not in painting_names:
    	flash("There's no such painting")
    	return redirect('/')
    else:
    	op1 = """select p.name,p.date,p.medium,p.painting_id,p.price,p.status,a.name,g.name 
		from painting_stored_included as p,created as c, gallery as g,artist as a 
		where p.painting_id=c.painting and c.artist=a.artist_id and p.gallery=g.gallery_id and p.name=(:name1)"""
    	cursor = g.conn.execute(text(op1), name1 = painting_name)
    	painting = cursor.fetchone()
    	cursor.close()	
    	session['painting_id'] = painting[3]
    	session['painting_name'] = painting[0]
    	session['painting_price'] = painting[4]
    	context = dict(painting = painting)
    return render_template("painting.html", **context)


@app.route("/painting_order")
def painting_order():
	order_items = session['painting_name']
	total_price = session['painting_price'] 
	user_id = session['user_id']
	op = 'SELECT status FROM painting_stored_included WHERE name = (:name)'
	cursor = g.conn.execute(text(op), name = order_items)
	status = cursor.fetchone()[0]
	cursor.close()
        if status == False:
		flash('The picture has been bought')
                return redirect("/")
	else:
		cursor = g.conn.execute('SELECT max(order_number) FROM order_made')
		order_number = cursor.fetchone()[0]
		cursor.close()
		order_number = order_number + 1
		op = 'INSERT INTO order_made(order_number,order_items,total_price,user_id) VALUES ((:a),(:b),(:c),(:d))'
		g.conn.execute(text(op),a = order_number, b = order_items,c = total_price, d = user_id)
		op = 'UPDATE painting_stored_included SET status = False, order_number = (:a) WHERE name = (:b)'
		g.conn.execute(text(op),a = order_number,b = order_items)
		flash('Thank you for purchasing')
                return redirect("/")
@app.route("/gallery",methods=['POST'])
def gallery():
    cursor = g.conn.execute("SELECT name FROM gallery")
    gallery_names = []
    for p in cursor:
    	print(p['name'])
        gallery_names.append(p['name'])
    cursor.close()		
    gallery_name = request.form['gallery']
    if gallery_name not in gallery_names:
    	flash("There's no such gallery")
    	return redirect('/')
    else:
    	op = 'SELECT * FROM gallery WHERE name = (:name)'
    	cursor = g.conn.execute(text(op), name = gallery_name)
    	gallery = cursor.fetchone()
    	cursor.close()
    	op = 'SELECT p.name from painting_stored_included as p, gallery as g where g.gallery_id = p.gallery and g.name = (:gallery_name)'
    	cursor = g.conn.execute(text(op), gallery_name = gallery_name)
     	paintings_stored = []
    	for n in cursor:
    		paintings_stored.append(n[0])      
        cursor.close()
    	op = 'SELECT m.membership_id from membership as m, gallery as g where g.gallery_id = m.affiliation and g.name = (:gallery_name)'
    	cursor = g.conn.execute(text(op), gallery_name = gallery_name)
    	membership_id = cursor.fetchone()
        cursor.close()
    	context = dict(gallery = gallery, paintings_stored = paintings_stored,membership_id = membership_id)	
        session['gallery_id'] = gallery['gallery_id']
    	return render_template('gallery.html', **context)

@app.route('/donate',methods = ['POST'])
def donate():
    amount = request.form['amount']
    cursor = g.conn.execute('SELECT max(donation_id) FROM donation')
    donation_id = cursor.fetchone()[0] + 1
    session['donation_id'] = donation_id
    cursor.close()
    op = 'INSERT INTO donation(amount, donation_id) VALUES ((:amount),(:donation_id)) '
    g.conn.execute(text(op), amount = amount, donation_id = donation_id)
    users = session['user_id']
    gallery = session['gallery_id']
    donation = session['donation_id']
    op = 'INSERT INTO donate_to(users,gallery,donation) VALUES ((:users),(:gallery),(:donation))'
    g.conn.execute(text(op), users = users, gallery = gallery, donation = donation)
    flash('Thanks for your donation')
    return redirect('/')
@app.route("/all_galleries")
def all_galleries():
    cursor = g.conn.execute("SELECT name FROM gallery")
    gallery_names = []
    for p in cursor:
        gallery_names.append(p['name'])
    cursor.close()

    context = dict(galleries = gallery_names)
    return render_template('all_galleries.html', **context)

@app.route('/all_artists')
def all_artists():
    cursor = g.conn.execute("SELECT name FROM artist")
    artist_names = []
    for p in cursor:
        artist_names.append(p['name'])
    cursor.close()

    context = dict(artist_names = artist_names)
    return render_template('all_artists.html', **context)

@app.route('/artist', methods=['POST'])
def artist():
    cursor = g.conn.execute("SELECT name FROM artist")
    artist_names = []
    for p in cursor:
        artist_names.append(p['name'])
    cursor.close()		
    artist_name = request.form['artist']
    if artist_name not in artist_names:
    	flash("There's no such artist")
    	return redirect('/')
    else:
    	op = 'SELECT * from artist where name = (:name)'
    	cursor = g.conn.execute(text(op), name = artist_name)
	artist = cursor.fetchone()
	cursor.close()
	op = 'SELECT p.name from artist as a,created as c,painting_stored_included as p where a.artist_id = c.artist and p.painting_id = c.painting and a.name = (:name)'    	
	cursor = g.conn.execute(text(op), name = artist_name)
	painting_created =[]
	for p in cursor:
		painting_created.append(p[0])
	cursor.close()
	context = dict(artist = artist, painting_created = painting_created)
	return render_template('artist.html', **context)


@app.route('/all_memberships')
def all_memberships():
    cursor = g.conn.execute("SELECT membership_id FROM membership")
    membership_ids = []
    for p in cursor:
        membership_ids.append(p['membership_id'])
    cursor.close()		
    context = dict(membership_ids = membership_ids)
    return render_template('all_memberships.html', **context)

@app.route('/membership',methods =['POST'] )
def membership():	
    cursor = g.conn.execute("SELECT membership_id FROM membership")
    membership_ids = []
    for p in cursor:
        membership_ids.append(str(p['membership_id']))
    cursor.close()		
    membership_id = request.form['membership']
    if membership_id not in membership_ids:
    	flash("There's no such membership")
    	return redirect('/')	
    else:
    	op = 'SELECT m.membership_id, g.name, m.price from membership as m, gallery as g where m.affiliation = g.gallery_id and m.membership_id = (:id)'
    cursor = g.conn.execute(text(op), id = membership_id )
    membership = cursor.fetchone()
    cursor.close()
    session['membership_id'] = membership[0]
    session['membership_price'] = membership[2]
    context = dict(membership = membership)
    return render_template('membership.html',**context)	




@app.route('/membership_order')
def membership_order():
    order_items = session['membership_id']
    total_price = session['membership_price'] 
    user_id = session['user_id']
    cursor = g.conn.execute('SELECT max(order_number) FROM order_made')
    order_number = cursor.fetchone()[0]
    cursor.close()
    order_number  = order_number + 1
    op = 'INSERT INTO order_made(order_number,order_items,total_price,user_id) VALUES ((:a),(:b),(:c),(:d))'
    g.conn.execute(text(op),a = order_number, b = order_items,c = total_price, d = user_id)
    op = "SELECT affiliation from membership where membership_id = (:id)"
    cursor = g.conn.execute(text(op), id = order_items )
    affiliation = cursor.fetchone()[0]
    op = 'INSERT INTO membership_included(affiliation,order_number,membership_id) values ((:a),(:b),(:c)) '
    g.conn.execute(text(op),a = affiliation, b = order_number, c = order_items)
    flash('Thanks for purchasing!')
    return redirect('/')

@app.route('/order_history')
def order_history():
    user_id = session['user_id']
    op = 'SELECT order_items, total_price from order_made where user_id = (:id)'
    cursor = g.conn.execute(text(op),id = user_id)
    order = []
    for c in cursor:
        order.append(c)
    context = dict(order = order)
    return render_template('order_history.html',**context)

@app.route('/donation_history')
def donation_history():
	user_id = session['user_id']
	op = 'SELECT g.name,d.amount from users as u, donation as d, gallery as g, donate_to as dt where u.user_id = dt.users and d.donation_id = dt.donation and g.gallery_id = dt.gallery and u.user_id = (:user_id)'
	cursor = g.conn.execute(text(op),user_id = user_id)
	donation  = []
	for c in cursor:
		donation.append(c)
	context = dict(donation  = donation)
	return render_template('donation_history.html',**context)



if __name__ == "__main__":
  import click
  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using
        python server.py
    Show the help text using
        python server.py --help
    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
