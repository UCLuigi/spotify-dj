from fastapi import FastAPI
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.oauth2 import SpotifyOAuth
import spotipy


SCOPES = [
    'user-top-read', 'playlist-read-private', 'user-read-private',
    'user-read-playback-state', 'user-read-recently-played',
    'user-read-currently-playing'
]
RECOMMENDATION_LIMIT = 5

app = FastAPI()


@app.get('/search')
def search(q: str) -> dict:
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    return sp.search(q)


@app.get('/tracks')
def get_tracks(tracks: list) -> dict:
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    return sp.tracks(tracks)


@app.get('/tracks/{track_id}')
def get_track(track_id: str) -> dict:
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    return sp.track(track_id)


@app.get('/audio-features')
def get_multiple_track_features(tracks: list) -> dict:
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    return sp.audio_features(tracks)


@app.get('/audio-features/{track_id}')
def get_track_features(track_id: str) -> dict:
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    return sp.audio_features([track_id])


@app.get('/audio-analysis/{track_id}')
def get_track_analysis(track_id: str) -> dict:
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    return sp.audio_analysis(track_id)


@app.get('/audio-analysis/{track_id}/soundwave')
def get_track_soundwave(track_id: str) -> list:
    """
    https://medium.com/swlh/creating-waveforms-out-of-spotify-tracks-b22030dd442b
    """
    features = get_track_analysis(track_id)

    duration = features['track']['duration']

    segments = []
    max_loudness = float('-inf')
    for segment in features['segments']:
        segment_loudness = 1 - \
            (min(max(segment['loudness_max'], -35), 0) / -35)
        segments.append({
            'start': segment['start'] / duration,
            'duration': segment['duration'] / duration,
            'loudness': segment_loudness
        })
        max_loudness = max(max_loudness, segment_loudness)

    levels = []
    for i in range(0, 1000):
        i_dec = i / 1000
        s = list(filter(lambda seg: i_dec <=
                 seg['start'] + seg['duration'], segments))[0]
        loudness = round((s['loudness'] / max_loudness) * 100) / 100
        levels.append(loudness)

    return levels


@app.get('/tracks/{track_id}/recommendations')
def get_recommendations(track_id: str, limit: int = RECOMMENDATION_LIMIT) -> dict:
    return get_track_recommendation_helper(track_id, limit)


@app.get('/me/player/currently-playing/recommendations')
def get_current_track_recommendations(limit: int = RECOMMENDATION_LIMIT) -> dict:
    return get_track_recommendation_helper(limit=limit)


def get_track_recommendation_helper(track_id: str = None,
                                    limit: int = RECOMMENDATION_LIMIT
                                    ) -> dict:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPES))

    if track_id is None:
        cur_track = sp.current_user_playing_track()['item']
    else:
        cur_track = sp.track(track_id)

    cur_track_id = cur_track['id']
    cur_track_features = sp.audio_features([cur_track_id])[0]

    rec_tracks = sp.recommendations(seed_tracks=[cur_track_id],
                                    limit=limit,
                                    target_tempo=cur_track_features['tempo'],
                                    target_danceability=cur_track_features['danceability'],
                                    target_energy=cur_track_features['energy']
                                    )['tracks']
    rec_features = sp.audio_features(
        [track['id'] for track in rec_tracks])

    recommendations = []
    for i, track_feature in enumerate(rec_features):
        recommendations.append(
            format_track_and_features(rec_tracks[i], track_feature)
        )

    return {
        'current_track': format_track_and_features(cur_track, cur_track_features),
        'recommendations': recommendations
    }


def format_track_and_features(track: dict, features: dict) -> dict:
    return {
        'id': track['id'],
        'artists': [artist['name'] for artist in track['artists']],
        'song': track['name'],
        'length_ms': track['duration_ms'],
        'preview_url': track['preview_url'],
        'features': {
            'tempo': features['tempo'],
            'danceability': features['danceability'],
            'energy': features['energy'],
            'loudness': features['loudness'],
            'mood': features['valence']
        }
    }


@app.get('/me/playlists')
def get_user_playlists() -> dict:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPES))
    return sp.current_user_playlists(limit=50)


@app.get('/playlists/{playlist_id}')
def get_playlist(playlist_id: str) -> dict:
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    return sp.playlist(playlist_id)


@app.get('/playlists/{playlist_id}/tracks')
def get_playlist_tracks(playlist_id: str) -> dict:
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    return sp.playlist_items(playlist_id)


@app.get('/me/top/artists')
def get_top_artists(limit: int = 20, time_range: str = 'medium_term') -> dict:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPES))
    return sp.current_user_top_artists(limit=limit, time_range=time_range)


@app.get('/me/top/tracks')
def get_top_tracks(limit: int = 20, time_range: str = 'medium_term') -> dict:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPES))
    return sp.current_user_top_tracks(limit=limit, time_range=time_range)


@app.get('/me/player/devices')
def get_user_devices() -> dict:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPES))
    return sp.devices()


@app.get('/me/player/currently-playing')
def get_current_track_playing() -> dict:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPES))
    return sp.current_user_playing_track()


@app.get('/me/player/recently-played')
def get_recently_played() -> dict:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPES))
    return sp.current_user_recently_played()


@app.get('/recommendations/available-genre-seeds')
def get_genre_seeds() -> list:
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    return sp.recommendation_genre_seeds()


@app.get('/me/player/recently-played/recommendations')
def get_recently_played_recommendations(lookback_limit: int = 3,
                                        rec_limit: int = RECOMMENDATION_LIMIT
                                        ) -> dict:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPES))

    recently_played_tracks = []
    cur_track = sp.current_user_playing_track()
    if cur_track is not None:
        cur_track = {'track': cur_track['item']}
        recently_played_tracks.append(cur_track)

    recently_played_tracks += sp.current_user_recently_played(
        limit=lookback_limit)['items']

    if len(recently_played_tracks) > 5:
        recently_played_tracks = recently_played_tracks[:5]

    recently_played_ids = [item['track']['id']
                           for item in recently_played_tracks]

    recently_played_features = sp.audio_features(recently_played_ids)

    limits = get_feature_limits_helper(recently_played_features)

    rec_tracks = sp.recommendations(seed_tracks=recently_played_ids,
                                    limit=rec_limit
                                    )['tracks']

    rec_features = sp.audio_features(
        [track['id'] for track in rec_tracks])

    recommendations = []
    for i, track_feature in enumerate(rec_features):
        recommendations.append(
            format_track_and_features(rec_tracks[i], track_feature)
        )

    formatted_recent_tracks = []
    for i, item in enumerate(recently_played_tracks):
        formatted_recent_tracks.append(format_track_and_features(
            item['track'], recently_played_features[i]))

    return {
        'recent_tracks': formatted_recent_tracks,
        'recommendations': recommendations
    }


def get_feature_limits_helper(track_features) -> dict:
    limits = {
        'tempo': {'min': float('inf'), 'max': float('-inf')},
        'danceability': {'min': float('inf'), 'max': float('-inf')},
        'energy': {'min': float('inf'), 'max': float('-inf')}
    }

    for limit in limits:
        feature_limits = [feature[limit] for feature in track_features]
        limits[limit]['average'] = sum(feature_limits) / len(track_features)
        limits[limit]['min'] = min(feature_limits)
        limits[limit]['max'] = max(feature_limits)

    return limits
