#----------------------------------------------------------------------------------------------------------------------------------------
#Librerias
import pandas as pd
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from time import sleep
from werkzeug.utils import secure_filename
#----------------------------------------------------------------------------------------------------------------------------------------
#Inicializaci[on] de la pagina
app = Flask(__name__)
app.secret_key = 'your_secret_key'

#----------------------------------------------------------------------------------------------------------------------------------------
#Variables globales
base_dir = os.path.abspath(os.path.dirname(__file__))
DataBase = os.path.join(base_dir, 'Resources', 'DB.xlsx')

UPLOAD_FOLDER = os.path.join(base_dir, 'uploads')
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

username = None
keyaccess = False
admin_user = ['sm10244', 'SM09035', 'SM01982','sm05556','SM10206']

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#/////////////////////////////////////////////////////////////////////////
@app.route('/')
def index():
    username = session.get('username')
    return render_template('index.html', username=username)

#/////////////////////////////////////////////////////////////////////////
#----------------------------------------------------------------------------------------------------------------------------------------
#Funcion de check user
@app.route('/set_user', methods=['POST'])
def set_user():
    session['username'] = request.form['username']
    return redirect(url_for('index'))

@app.route('/check_user')
def check_user():
    global keyaccess
    username = session.get('username')
    if not username:
        return redirect(url_for('index'))
    try:
        df = pd.read_excel(DataBase, sheet_name='Participantes', engine='openpyxl')
        if username in df['Usuario'].values:
            if username in admin_user:
                keyaccess = True
                return redirect(url_for('stats'))
        else:
            new_user = pd.DataFrame({'Usuario': [username]})
            df = pd.concat([df, new_user], ignore_index=True)
            with pd.ExcelWriter(DataBase, engine='openpyxl', mode='a', if_sheet_exists="replace") as writer:
                df.to_excel(writer, sheet_name='Participantes', index=False)
            flash("El usuario ha sido añadido a la base de datos.")
        flash(f"Bienvenido {username}")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Ha ocurrido un error: {e}")
        return redirect(url_for('index'))


#----------------------------------------------------------------------------------------------------------------------------------------
#Funcion para desplegar canciones
@app.route('/display_songs')
def display_songs():
    try:
        df = pd.read_excel(DataBase, sheet_name='Lista Global', engine='openpyxl')
        songs = df.to_dict(orient='records')
        return render_template('songs.html', songs=songs)
    except Exception as e:
        flash(f"Ha ocurrido un error: {e}")
        return redirect(url_for('index'))
#----------------------------------------------------------------------------------------------------------------------------------------
#Funcion para desplegar canciones actuales
@app.route('/display_songs_week')
def display_songs_week():
    try:
        df = pd.read_excel(DataBase, sheet_name='Lista Global', engine='openpyxl')
        current_week = int(pd.Timestamp.now().strftime('%U'))
        weekly_songs = df[df['Fecha'] == current_week].to_dict(orient='records')
        return render_template('weekly_songs.html', songs=weekly_songs)
    except Exception as e:
        flash(f"Ha ocurrido un error: {e}")
        return redirect(url_for('index'))

#----------------------------------------------------------------------------------------------------------------------------------------
#Funcion de añadir canciones
@app.route('/show_add_page')
def show_add_page():
    return render_template('add.html')

@app.route('/add_songs', methods=['POST'])
def add_songs():
    username = session.get('username')
    songs = request.form.getlist('songs')
    artists = request.form.getlist('artists')
    if not all(songs) or not all(artists) or len(songs) != 4 or len(artists) != 4:
        flash("Por favor, asegúrate de que todos los campos de canciones y artistas estén llenos y contengan cuatro valores.")
        return redirect(url_for('show_add_page'))
    try:
        df = pd.read_excel(DataBase, sheet_name='Lista Global', engine='openpyxl')
        week = pd.Timestamp.now().strftime('%U')
        new_songs = pd.DataFrame({
            'Fecha': [week]*4,
            'Cancion': songs,
            'Artista': artists,
            'Subida por': [username]*4,
            'Votos': [0]*4,
            'Votos -': [0]*4
        })
        df = pd.concat([df, new_songs], ignore_index=True)
        with pd.ExcelWriter(DataBase, engine='openpyxl', mode='a', if_sheet_exists="replace") as writer:
            df.to_excel(writer, sheet_name='Lista Global', index=False)
        flash("Las canciones han sido añadidas a la base de datos.")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Ha ocurrido un error: {e}")
        return

#----------------------------------------------------------------
@app.route('/add_songs_from_csv',  methods=['GET', 'POST'])
def add_songs_from_csv():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No se ha seleccionado ningún archivo CSV.')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No se ha seleccionado ningún archivo CSV.')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            try:
                # Read the CSV file
                csv_df = pd.read_csv(filepath)
                if csv_df.empty:
                    flash('El archivo CSV subido está vacío.')
                    return redirect(url_for('show_add_page'))

                DB_DF = pd.read_excel(DataBase)
                User_spotify = []
                for tag in csv_df['addedBy']:
                    user_name = str(DB_DF.loc[DB_DF['SpotiTag'] == tag, 'Name'].values[0])
                    User_spotify.append(user_name)

                # Extract relevant columns and add current week
                current_week = pd.Timestamp.now().strftime('%U')
                new_songs = pd.DataFrame({
                    'Fecha': [current_week] * len(csv_df),
                    'Cancion': csv_df['title'],
                    'Artista': csv_df['artist'],
                    'Subida por': User_spotify,
                    'Votos': [0] * len(csv_df),
                    'Votos -': [0] * len(csv_df)
                })

                # Read the existing Excel file
                df = pd.read_excel(DataBase, sheet_name='Lista Global', engine='openpyxl')

                # Concatenate the new songs with the existing dataframe
                df = pd.concat([df, new_songs], ignore_index=True)

                # Write the updated dataframe to the Excel file
                with pd.ExcelWriter(DataBase, engine='openpyxl', mode='a', if_sheet_exists="replace") as writer:
                    df.to_excel(writer, sheet_name='Lista Global', index=False)

                flash("Las canciones del CSV han sido añadidas a la base de datos.")
                return redirect(url_for('index'))
            except Exception as e:
                flash(f"Ha ocurrido un error: {e}")
                return redirect(url_for('show_add_page'))
    return render_template('upload.html')


#----------------------------------------------------------------
#Funcion para mostrar estadisticas
@app.route('/stats')
def stats():
    if not keyaccess:
        flash("Acceso denegado.")
        sleep(3000)
        return redirect(url_for('index'))
    return render_template('stats.html')

#----------------------------------------------------------------------------------------------------------------------------------------
#Funcion de votos a favor y en contra
@app.route('/vote', methods=['GET', 'POST'])
def vote_songs():
    username = session.get('username')
    try:
        if request.method == 'POST':
            df = pd.read_excel(DataBase, sheet_name='Lista Global', engine='openpyxl')
            df_participants = pd.read_excel(DataBase, sheet_name='Participantes', engine='openpyxl')
            user_name = df_participants.loc[df_participants['Usuario'] == username, 'Name'].values[0]
            current_week = int(pd.Timestamp.now().strftime('%U'))

            selected_songs = request.form.getlist('selected_songs')
            selected_culey = request.form.get('selected_culey')

            if len(selected_songs) != 8 and len(selected_culey) != 1 :
                flash("Por favor, selecciona exactamente 8 canciones y 1 cancion culey.")
                return redirect(url_for('vote_songs'))

            for song in selected_songs:
                if df.loc[(df['Cancion'] == song) & (df['Fecha'] == current_week), 'Subida por'].values[0] == user_name:
                    flash("Por favor, selecciona canciones que no sean tuyas.")
                    return redirect(url_for('vote_songs'))

            if df.loc[(df['Cancion'] == selected_culey) & (df['Fecha'] == current_week), 'Subida por'].values[0] == user_name:
                flash("Por favor, selecciona canciones que no sean tuyas.")
                return redirect(url_for('vote_songs'))

            user_votes = df_participants[df_participants['Usuario'] == username]
            if not user_votes.empty and not user_votes[user_votes['Fecha'] == current_week].empty and not pd.isna(user_votes[user_votes['Fecha'] == current_week].iloc[0].get('Voto 1', None)):
                flash("Ya has votado esta semana.")
                return redirect(url_for('vote_songs'))

            for song in selected_songs:
                df.loc[(df['Cancion'] == song) & (df['Fecha'] == current_week), 'Votos'] += 1

            df.loc[(df['Cancion'] == selected_culey) & (df['Fecha'] == current_week), 'Votos -'] += 1

            if user_votes.empty:
                new_vote = pd.DataFrame({
                    'Usuario': [username],
                    'Fecha': [current_week],
                    'Voto 1': [selected_songs[0]],
                    'Voto 2': [selected_songs[1]],
                    'Voto 3': [selected_songs[2]],
                    'Voto 4': [selected_songs[3]],
                    'Voto 5': [selected_songs[4]],
                    'Voto 6': [selected_songs[5]],
                    'Voto 7': [selected_songs[6]],
                    'Voto 8': [selected_songs[7]],
                    'Voto Culey': [selected_culey]
                })
                df_participants = pd.concat([df_participants, new_vote], ignore_index=True)
            else:
                df_participants[['Voto 1', 'Voto 2', 'Voto 3', 'Voto 4', 'Voto 5', 'Voto 6', 'Voto 7', 'Voto 8', 'Voto Culey']] = df_participants[['Voto 1', 'Voto 2', 'Voto 3', 'Voto 4', 'Voto 5', 'Voto 6', 'Voto 7', 'Voto 8', 'Voto Culey']].astype(str)
                df_participants.loc[df_participants['Usuario'] == username, ['Voto 1', 'Voto 2', 'Voto 3', 'Voto 4', 'Voto 5', 'Voto 6', 'Voto 7', 'Voto 8', 'Voto Culey', 'Fecha']] = [selected_songs[0], selected_songs[1], selected_songs[2], selected_songs[3], selected_songs[4], selected_songs[5], selected_songs[6], selected_songs[7], selected_culey, current_week]

            with pd.ExcelWriter(DataBase, engine='openpyxl', mode='a', if_sheet_exists="replace") as writer:
                df.to_excel(writer, sheet_name='Lista Global', index=False)
                df_participants.to_excel(writer, sheet_name='Participantes', index=False)

            flash("Tus votos han sido registrados.")
            return redirect(url_for('index'))

        else:
            df = pd.read_excel(DataBase, sheet_name='Lista Global', engine='openpyxl')
            current_week = int(pd.Timestamp.now().strftime('%U'))
            songs = df[df['Fecha'] == current_week].to_dict(orient='records')
            return render_template('vote_songs.html', songs=songs)

    except Exception as e:
        flash(f"Ha ocurrido un error: {e}")
        return redirect(url_for('index'))
#----------------------------------------------------------------------------------------------------------------------------------------
#Funcion para calcular mayoria de votos
@app.route('/most_voted_songs')
def most_voted_songs():
    try:
        dataframe = pd.read_excel(DataBase, sheet_name='Lista Global', engine='openpyxl')
        # Group by song and sum the votes
        vote_counts = dataframe.groupby(['Fecha', 'Cancion', 'Subida por'])['Votos'].sum().reset_index()

        # Filter out songs with no votes and not in the current week
        current_week = int(pd.Timestamp.now().strftime('%U'))
        vote_counts = vote_counts[(vote_counts['Votos'] > 0) & (vote_counts['Fecha'] == current_week)]

        # Sort the dataframe by votes in descending order
        vote_counts = vote_counts.sort_values(by='Votos', ascending=False)
        #vote_counts = vote_counts.head(10)

        # Get the top 3 songs
        top_3_songs = vote_counts.head(3)

        return render_template('most_voted_song.html', vote_counts=vote_counts.to_dict(orient='records'), top_3_songs=top_3_songs.to_dict(orient='records'))
    except Exception as e:
        flash(f"Ha ocurrido un error: {e}")
        return redirect(url_for('index'))

#----------------------------------------------------------------------------------------------------------------------------------------
#Funcion cancion mas odiada
@app.route('/most_hated_songs')
def most_hated_songs():
    try:
        dataframe = pd.read_excel(DataBase, sheet_name='Lista Global', engine='openpyxl')
        # Group by song and sum the negative votes
        vote_counts = dataframe.groupby(['Fecha', 'Cancion', 'Subida por'])['Votos -'].sum().reset_index()

        # Filter out songs with no negative votes and not in the current week
        current_week = int(pd.Timestamp.now().strftime('%U'))
        vote_counts = vote_counts[(vote_counts['Votos -'] > 0) & (vote_counts['Fecha'] == current_week)]

        # Sort the dataframe by negative votes in descending order
        vote_counts = vote_counts.sort_values(by='Votos -', ascending=False)

        # Get the top 3 songs with the most negative votes
        top_3_songs = vote_counts.head(3)

        return render_template('most_hated_songs.html', vote_counts=vote_counts.to_dict(orient='records'), top_3_songs=top_3_songs.to_dict(orient='records'))
    except Exception as e:
        flash(f"Ha ocurrido un error: {e}")
        return redirect(url_for('index'))

#----------------------------------------------------------------------------------------------------------------------------------------
#Funcion para calcular quien tiene mas votos
@app.route('/top_global')
def top_global():
    try:
        dataframe = pd.read_excel(DataBase, sheet_name='Lista Global', engine='openpyxl')
        # Group by uploader and sum the votes
        user_vote_counts = dataframe.groupby('Subida por')['Votos'].sum().reset_index()

        # Sort the dataframe by votes in descending order
        user_vote_counts = user_vote_counts.sort_values(by='Votos', ascending=False)

        # Get the top 5 users
        top_5_users = user_vote_counts

        return render_template('top_global.html', top_5_users=top_5_users.to_dict(orient='records'))
    except Exception as e:
        flash(f"Ha ocurrido un error: {e}")
        return redirect(url_for('index'))

#----------------------------------------------------------------------------------------------------------------------------------------
#Funcion para calcular mayoria de votos negativos
@app.route('/hate_global')
def hate_global():
    try:
        dataframe = pd.read_excel(DataBase, sheet_name='Lista Global', engine='openpyxl')
        # Group by uploader and sum the votes
        user_vote_counts = dataframe.groupby('Subida por')['Votos -'].sum().reset_index()

        # Sort the dataframe by votes in descending order
        user_vote_counts = user_vote_counts.sort_values(by='Votos -', ascending=False)

        # Get the top 5 users
        top_5_users = user_vote_counts

        return render_template('hate_global.html', top_5_users=top_5_users.to_dict(orient='records'))
    except Exception as e:
        flash(f"Ha ocurrido un error: {e}")
        return redirect(url_for('index'))

#----------------------------------------------------------------------------------------------------------------------------------------
#Funcion para ver los votos semanales
@app.route('/votos_semanales')
def votos_semanales():
    try:
        dataframe = pd.read_excel(DataBase, sheet_name='Lista Global', engine='openpyxl')
        current_week = int(pd.Timestamp.now().strftime('%U'))
        votosemanal = dataframe[dataframe['Fecha'] == current_week].groupby('Subida por')['Votos'].sum().reset_index()
        votosemanal = votosemanal.sort_values(by='Votos', ascending=False)
        votosemanal2 = dataframe[dataframe['Fecha'] == current_week].groupby('Subida por')['Votos -'].sum().reset_index()
        votosemanal2 = votosemanal2.sort_values(by='Votos -', ascending=False)
        return render_template('votos_semanales.html', votosemanal=votosemanal.to_dict(orient='records'), votosemanal2=votosemanal2.to_dict(orient='records'))

    except Exception as e:
        flash(f"Ha ocurrido un error: {e}")
        return redirect(url_for('index'))

#----------------------------------------------------------------------------------------------------------------------------------------
#Funcion para ver quien falta de votar
@app.route('/missing_votes')
def missing_votes():
    try:
        df_participants = pd.read_excel(DataBase, sheet_name='Participantes', engine='openpyxl')

        # Filter participants who haven't voted this week
        missing_voters = df_participants[pd.isna(df_participants['Voto 1'])]

        # Get the names from the 'Subida por' column
        missing_voters_names = missing_voters['Name'].tolist()
        #print(missing_voters_names)

        return render_template('missing_votes.html', missing_voters=missing_voters_names)
    except Exception as e:
        flash(f"Ha ocurrido un error: {e}")
        return redirect(url_for('index'))

#----------------------------------------------------------------
#MAIN
if __name__ == '__main__':
    app.run()

    """"
#----------------------------------------------------------------------------------------------------------------------------------------
"""