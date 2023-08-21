import configparser
from itertools import islice

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth


def split_every(n, iterable):
    i = iter(iterable)
    piece = list(islice(i, n))
    while piece:
        yield piece
        piece = list(islice(i, n))


class SpotipyWrapper:
    spotify: spotipy.Spotify

    def __init__(self, spotify: spotipy.Spotify):
        self.spotify = spotify

    def get_liked_tracks_from_playlist(self, playlist_id):
        fields = "items(track(track_number,disc_number,name,uri,id,album(name))),next"

        playlist = self.spotify.playlist_items(playlist_id=playlist_id, fields=fields, limit=50)

        while True:
            liked_items = []
            track_ids = [item["track"]["id"] for item in playlist["items"]]
            saved_tracks_contains = self.spotify.current_user_saved_tracks_contains(tracks=track_ids)

            for i, track in enumerate(track_ids):
                if saved_tracks_contains[i]:
                    liked_items.append(playlist["items"][i])

            yield liked_items

            if not playlist["next"]:
                return
            else:
                playlist = self.spotify.next(playlist)

    def move_tracks_to_other_playlist(self, source_playlist, destination_playlist, track_uris):
        batch_size = 100
        for i, fifty_tracks in enumerate(split_every(batch_size, track_uris)):
            self.spotify.playlist_add_items(playlist_id=destination_playlist, items=fifty_tracks,
                                            position=(i * batch_size))
            self.spotify.playlist_remove_all_occurrences_of_items(playlist_id=source_playlist, items=fifty_tracks)


def main():
    load_dotenv()
    config = configparser.ConfigParser()
    config.read("config.ini")

    src_playlist = config["spotify"]["SourcePlaylist"]
    dst_playlist = config["spotify"]["DestinationPlaylist"]

    scopes = ["user-library-read", "playlist-modify-public", "playlist-modify-private"]

    spotify = spotipy.Spotify(client_credentials_manager=SpotifyOAuth(scope=scopes))
    wrapper = SpotipyWrapper(spotify)

    all_liked_tracks = []

    for liked_tracks in wrapper.get_liked_tracks_from_playlist(src_playlist):
        all_liked_tracks.extend(liked_tracks)

    sorted_liked_tracks = list(sorted(all_liked_tracks,
                                      key=lambda track: (
                                          track["track"]["album"]["name"],
                                          track["track"]["disc_number"],
                                          track["track"]["track_number"]
                                      )))

    print(*sorted_liked_tracks, sep="\n")

    track_uris_to_move = [liked["track"]["uri"] for liked in sorted_liked_tracks]
    wrapper.move_tracks_to_other_playlist(src_playlist, dst_playlist, track_uris_to_move)


if __name__ == '__main__':
    main()
