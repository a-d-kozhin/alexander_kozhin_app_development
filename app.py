import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta


def connect_to_mongo(uri):
    return MongoClient(uri)


def get_database(client, db_name):
    return client[db_name]


mongo_client = connect_to_mongo(st.secrets["mongodb_uri"])
auth_db = get_database(mongo_client, 'app_development')
user_collection = auth_db['users']
st.set_page_config(page_title="Mind Arena", page_icon="🧠", layout="wide")

background_image = """
<style>
[data-testid = "stAppViewContainer"] {
background-image: url('https://images.unsplash.com/photo-1588345921523-c2dcdb7f1dcd');
background-size: cover;
}
</style>
"""
st.markdown(background_image, unsafe_allow_html=True)

# Function to display a card (book, or movie)
def display_item(item, media_type):
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(item['image_url'], width=250)
    with col2:
        st.subheader(item['title'])
        if media_type == "book":
            st.caption(f"By {item['author']} ({item['year']})")
        elif media_type == "movie":
            st.caption(f"Directed by {item['director']} ({item['year']})")
        if st.button("Challenge Yourself", key=f"challenge_{media_type}_{item['title']}"):
            add_challenge(item['title'], media_type)
        if st.button("Share Challenge", key=f"share_{media_type}_{item['title']}"):
            challenge_text = f"I challenge you to a {media_type}: {item['title']}! Join me on Mind Arena."
            st.text_area("Copy this challenge and send it to your friend:", challenge_text,
                         key=f"textarea_{media_type}_{item['title']}")

# Function to create a carousel,
# which contains an item (card) column, and an arrow column – for positioning purposes
def create_carousel(category, items, media_type):
    index = st.session_state.get(f"{category}_index", 0)
    st.subheader(category)
    item_col, arrow_col = st.columns([15, 1])
    with item_col:
        display_item(items[index], media_type)
# ! Important: only works with entities that contain only 3 items.
# In other cases, a modification would be needed
    with arrow_col:
        if st.button("→", key=f"next_{category}"):
            next_book_index = (index + 1) % 3
            st.session_state[f"{category}_index"] = next_book_index
            st.rerun()

# Function to add challenges
def add_challenge(name, type):
    for challenge in st.session_state.challenges:
        # A check to prevent challenge duplication
        if challenge[0] == name:
            st.warning(f"The challenge '{name}' already exists.")
            return

    today = datetime.now()
    # Deadlines depend on the type of media: 7 for movies and 30 for books
    deadline = today + timedelta(days=7) if type == "movie" else today + timedelta(days=30)
    st.session_state.challenges.append((name, type, today, deadline))
    st.success(f"Challenge '{name}' added!")

# Delete active challenges from the state
# This function would need to modify the API, if the active challenges were stored dynamically
def remove_challenge(name_to_remove):
    st.session_state.challenges = [
        challenge for challenge in st.session_state.challenges
        if challenge[0] != name_to_remove
    ]

# Logged in state is used to show either Welcome page or the Home page
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
# This state is used to greet the user with their name
if 'current_user_name' not in st.session_state:
    st.session_state['current_user_name'] = ''
# This state is used to store the selected challenges
# It would be much better to store them in the DB
if 'challenges' not in st.session_state:
    st.session_state.challenges = []

# For users who are not logged in
# shows the Welcome page with Login/Register buttons
if not st.session_state.get('logged_in', False):

    with st.form("AuthForm", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        col1, col2 = st.columns([1, 1])
        with col1:
            login_submit = st.form_submit_button("Login")
        with col2:
            register_submit = st.form_submit_button("Sign Up")

    if login_submit or register_submit:
        if not username or not password:
            st.error("Please enter both username and password.")
        else:
            if login_submit:
                user_doc = user_collection.find_one({"username": username})
                if user_doc and password == user_doc.get('password'):
                    # Important to update the state
                    st.session_state['logged_in'] = True
                    st.session_state['current_user_name'] = username
                    # Something was not working properly without rerun, so I added it
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")

            if register_submit:
                if user_collection.find_one({"username": username}):
                    st.error("This username already exists. Please choose another.")
                else:
                    user_collection.insert_one({"username": username, "password": password})
                    # Important to update the state
                    st.session_state['current_user_name'] = username
                    st.session_state['logged_in'] = True
                    # Something was not working properly without rerun, so I added it
                    st.rerun()

# Logged in users can see the sidebar and the Homepage

if st.session_state.logged_in:
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Curated Books", "Curated Movies"])

# Home page is showed after logging in or registering
    if page == "Home":
        st.title("Mind Arena")
        st.write('Challenge yourself or your friends to appreciate content that is worth your time.')

        st.header(f"Hello, {st.session_state['current_user_name'].capitalize()}!")

        st.subheader("Getting Started with Mind Arena")
        # I think it would be better to show this on click and have initially hidden
        st.write("""
        **Step 1: Find Your Challenge** - Go to 'Curated books' or 'Curated movies' to see the brilliant literature and movies, carefully selected by the experts.

        **Step 2: Challenge yourself** - When you click on the button 'challenge yourself', this challenge adds to your Active Challenges list on this page.

        **Step 3: Challenge friends** - When you click on the button 'share challenge', an invite-message is generated.

        **Step 4: Keep up with time** - You will have 30 days to read the book, and 7 days to watch a movie! Try to finish the challenge in time.
        
        **Step 5: Explore More** - Mind Arena is constantly updated with new curated lists. Stay with us!
        """)

        st.write("Dive into the challenges and discover something new today.")

        st.subheader("Your active Challenges:")

        # Would be better to fetch the challenges from the DB,
        # in this case they would save after logging out or refreshing the page
        for challenge in st.session_state.challenges:
            challenge_name, type, created, deadline = challenge
            days_remaining = (deadline - datetime.now()).days
            challenge_text = f"* Challenge: {challenge_name} ({'watch' if type == 'movie' else 'read'} within {days_remaining} days)"
            challenge_line = st.empty()
            remove_button = st.button("Remove", key=f"remove_{challenge_name}")

            if remove_button:
                remove_challenge(challenge_name)
                challenge_line.markdown("")
                st.rerun()
            else:
                challenge_line.markdown(challenge_text)
    # Is shown if the Curated books tab is selected
    if page == "Curated Books":
        st.title("Books to Ignite Your Imagination")
        st.markdown("Thoughtfully selected masterpieces")
        # Would be better to store them in the DB, and get them from there
        curated_book_lists = {
            "3 Hidden Gems of Russian Classics to Read This March": [
                {"title": "Fathers and Sons", "author": "Ivan Turgenev", "year": "1862",
                 "image_url": "https://m.media-amazon.com/images/I/41JrpnqYYtS._SL500_.jpg"},
                {"title": "The Death of Ivan Ilyich", "author": "Leo Tolstoy", "year": "1886",
                 "image_url": "https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1663546974i/18386.jpg"},
                {"title": "Pnin", "author": "Vladimir Nabokov", "year": "1957",
                 "image_url": "https://m.media-amazon.com/images/I/41GaSfduMiL.jpg"},
            ],
            "3 Inspiring Biographies to Read This Spring": [
                {"title": "The Diary of a Young Girl", "author": "Anne Frank", "year": "1947",
                 "image_url": "https://m.media-amazon.com/images/I/71qeWx83sxL._AC_UF894,1000_QL80_.jpg"},
                {"title": "Einstein: His Life and Universe", "author": "Walter Isaacson", "year": "2007",
                 "image_url": "https://m.media-amazon.com/images/I/71M6EivDCnL._AC_UF1000,1000_QL80_.jpg"},
                {"title": "Long Walk to Freedom", "author": "Nelson Mandela", "year": "1994",
                 "image_url": "https://images.thalia.media/03/-/fe9c943787f3481b9b4c880b38af1610/long-walk-to-freedom-vol-1-epub-nelson-mandela.jpeg"},
            ],
            "3 Exciting Pageturners for Rainy Spring Evenings": [
                {"title": "The Night Circus", "author": "Erin Morgenstern", "year": "2011",
                 "image_url": "https://cdn.kobo.com/book-images/ebd620dd-420e-4e9f-820c-c24b91401d97/353/569/90/False/the-night-circus-2.jpg"},
                {"title": "Rebecca", "author": "Daphne du Maurier", "year": "1938",
                 "image_url": "https://m.media-amazon.com/images/I/91ziTMetVcL._AC_UF894,1000_QL80_.jpg"},
                {"title": "The Seven Husbands of Evelyn Hugo", "author": "Taylor Jenkins Reid", "year": "2017",
                 "image_url": "https://m.media-amazon.com/images/I/710QvWhZIwL._AC_UF894,1000_QL80_.jpg"},
            ],
        }
        for category, books in curated_book_lists.items():
            create_carousel(category, books, "book")

    # Is shown if the Curated Movies tab is selected
    if page == "Curated Movies":
        st.title("Curated Movies for Every Taste")
        st.markdown("Thoughtfully selected masterpieces")
        # Would be better to store them in the DB, and get them from there
        curated_movie_lists = {
            "3 Must-Watch Tarkovsky Movies for March": [
                {"title": "Andrei Rublev", "director": "Andrei Tarkovsky", "year": "1966",
                 "image_url": "https://m.media-amazon.com/images/M/MV5BNjM2MjMwNzUzN15BMl5BanBnXkFtZTgwMjEzMzE5MTE@._V1_.jpg"},
                {"title": "Solaris", "director": "Andrei Tarkovsky", "year": "1972",
                 "image_url": "https://m.media-amazon.com/images/M/MV5BZmY4Yjc0OWQtZDRhMy00ODc2LWI2NGYtMWFlODYyN2VlNDQyXkEyXkFqcGdeQXVyNjU0OTQ0OTY@._V1_FMjpg_UX1000_.jpg"},
                {"title": "Stalker", "director": "Andrei Tarkovsky", "year": "1979",
                 "image_url": "https://resizing.flixster.com/-XZAfHZM39UwaGJIFWKAE8fS0ak=/v3/t/assets/p17498_p_v8_ai.jpg"},
            ],
            "3 Classic Noir Films for a Cozy Movie Night": [
                {"title": "Double Indemnity", "director": "Billy Wilder", "year": "1944",
                 "image_url": "https://upload.wikimedia.org/wikipedia/commons/c/ce/Double_Indemnity_%281944_poster%29.jpg"},
                {"title": "The Maltese Falcon", "director": "John Huston", "year": "1941",
                 "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/The_Maltese_Falcon_%281941_film_poster%29.jpg/676px-The_Maltese_Falcon_%281941_film_poster%29.jpg"},
                {"title": "The Third Man", "director": "Carol Reed", "year": "1949",
                 "image_url": "https://assets.mubicdn.net/images/notebook/post_images/19045/images-w1400.jpg?1434921963"},
            ],
            "3 Hitchcock Masterpieces for Suspenseful Evenings": [
                {"title": "Psycho", "director": "Alfred Hitchcock", "year": "1960",
                 "image_url": "https://m.media-amazon.com/images/I/610L8FnFWpL._AC_UF1000,1000_QL80_.jpg"},
                {"title": "Rear Window", "director": "Alfred Hitchcock", "year": "1954",
                 "image_url": "https://i.pinimg.com/474x/d3/a1/78/d3a178c03640f3361493158b4dd699e7.jpg"},
                {"title": "Vertigo", "director": "Alfred Hitchcock", "year": "1958",
                 "image_url": "https://m.media-amazon.com/images/I/91p7axI7JUS.jpg"},
            ],
        }

        for category, movies in curated_movie_lists.items():
            create_carousel(category, movies, "movie")
    # Logging out function
    if st.sidebar.button("Logout"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()
