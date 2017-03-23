# This sample uses code from https://pythonhosted.org/Flask-OAuth/ for OAuth1 login with Twitter
from flask import Flask, request, redirect, url_for, session, g, flash, \
     render_template
from flask_oauth import OAuth
from qb import create_customer, add_customer
import json
from utils import excel 
from utils import configRead

# configuration
SECRET_KEY = 'prod key'
DEBUG = True
font_color = 'black'
consumer_tokens = configRead.get_consumer_tokens()
oauth_url = configRead.get_oauth_urls()

# setup flask
app = Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY
oauth = OAuth()

qbo = oauth.remote_app('qbo',
    base_url=oauth_url['base_url'],
    request_token_url=oauth_url['request_token_url'],
    access_token_url=oauth_url['access_token_url'],
    authorize_url=oauth_url['authorize_url'],
    consumer_key=consumer_tokens['consumer_key'],
    consumer_secret=consumer_tokens['consumer_sec']
)
 
@qbo.tokengetter
def get_qbo_token(token=None):
    if session.has_key('qbo_token'):
        del session['qbo_token'] 
    return session.get('qbo_token')
 
@app.route('/')
def index():
    access_token = session.get('access_token')
    if access_token is None:
        return redirect(url_for('login'))
 
    access_token = access_token[0]
    global customer_list
    customer_list = excel.load_excel()
 
    return render_template('index.html', 
        customer_dict=customer_list,
        title="QB Customer Leads",
        text_color=font_color)

#test based
@app.route('/', methods=['GET','POST'])
def update_table():
    customer_id = request.form['id']
    for customer in customer_list:
        if customer['Id'] == customer_id:

            # Create customer object, add customer to qbo and get response
            access_tokens = session.get('qbo_token')
            realm_id = session.get('realm_id')
            customer_obj = create_customer(customer)
            
            req_status_content = add_customer(customer_obj, realm_id, access_tokens[0], access_tokens[1])
            status_code = req_status_content['status_code']
            content = json.loads(req_status_content['content'])

            global message
            global font_color
            # If customer added successfully, remove them from html and excel file
            if (status_code == 200):
                font_color = 'green'
                new_customer_list = excel.remove_lead(customer_list, customer_id)
                message = "Success! Customer added to QBO"
                flash(message)

                return render_template('index.html',
                                       customer_dict=new_customer_list,
                                       title="QB Customer Leads",
                                       text_color=font_color)
            
            #If customer not found, show error message
            else:
                font_color = 'red'
                try:
                    message = content['Fault']['Error'][0]['Message']
                except:
                        message = "Some error occurred. Error message not found."
            
    flash(message)
    return redirect(url_for('index'))
 
@app.route('/login')
def login():
    return qbo.authorize(callback=url_for('oauth_authorized',
        next=request.args.get('next') or request.referrer or None))
 
@app.route('/reset_session')
def reset_session():
    session.pop('qbo_token', None)
    session['is_authorized'] = False
    return redirect(request.referrer or url_for('index'))
 
@app.route('/oauth-authorized')
@qbo.authorized_handler
def oauth_authorized(resp):
    realm_id = str(request.args.get('realmId'))
    next_url = request.args.get('next') or url_for('index')
    if resp is None:
        flash(u'You denied the request to sign in.')
        return redirect(next_url)
 
    access_token = resp['oauth_token']
    session['access_token'] = access_token
    session['is_authorized'] = True
    session['realm_id'] = realm_id
    session['qbo_token'] = (
        resp['oauth_token'],
        resp['oauth_token_secret']
    )
    return redirect(url_for('index'))
 
if __name__ == '__main__':
    app.run()