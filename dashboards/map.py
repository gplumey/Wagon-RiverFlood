# import altair as alt
import os
from timeit import default_timer as timer

import folium
import pendulum
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
from streamlit_folium import st_folium


def get_service_account_credentials():
    # get the GCP credentials once if not already in session_state
    if 'credentials' not in st.session_state:
        private_key = os.getenv('GCP_JSON_PRIVATE_KEY')
        if private_key is None:
            st.error("Environment variable 'GCP_JSON_PRIVATE_KEY' not set")
            st.stop()
        secrets = st.secrets["gcp_service_account"]
        service_account_info = {
            "type": secrets["type"],
            "project_id": secrets["project_id"],
            "private_key_id": secrets["private_key_id"],
            "private_key": private_key,
            "client_email": secrets["client_email"],
            "client_id": secrets["client_id"],
            "auth_uri": secrets["auth_uri"],
            "token_uri": secrets["token_uri"],
            "auth_provider_x509_cert_url": secrets["auth_provider_x509_cert_url"],
            "client_x509_cert_url": secrets["client_x509_cert_url"],
        }
        credentials = service_account.Credentials.from_service_account_info(service_account_info)
        # Create credentials using the constructed dictionary and store in session state
        st.session_state.credentials = credentials
    credentials = st.session_state.credentials

    return credentials


def get_client(credentials):
    if "client" not in st.session_state:
        st.session_state.client = bigquery.Client(credentials=credentials, location="EU")
    client = st.session_state.client
    return client


@st.cache_data(ttl=600)
def get_historical_data(_client):
    # Use the function to get credentials

    query = (
        # f"""SELECT *
        # FROM `riverflood-lewagon.river_observation_dev.hubeau_historical_bronze`
        # where (latitude between 0 AND 90) and (longitude between 0 AND 5)
        # limit 2000;
        # """
        f"""SELECT *
        FROM `riverflood-lewagon.river_observation_dev.hubeau_indicator_latest`
--         where (latitude between 0 AND 90) and (longitude between 0 AND 5)
        """

    )
    df = _client.query(query).to_dataframe()
    return df


def get_map(df):
    if "map" not in st.session_state:
        locs_map = folium.Map(
            location=[46.856614, 2.3522219],
            zoom_start=6, tiles="cartodbpositron",
            zoom_control=True,
            scrollWheelZoom=False
        )
        # fmc = plugins.FastMarkerCluster(df[['latitude', 'longitude']].values.tolist())
        # locs_map.add_child(fmc)

        # for i in range(0,len(df)):
        #     folium.Marker(
        #         location=[df.iloc[i]["latitude"], df.iloc[i]["longitude"]],
        #         popup=df.iloc[i]["code_station"],
        #         icon=folium.Icon(
        #             icon="flag",
        #             color=("red" if df.iloc[i]["resultat_obs_elab"] > 1000 else "blue"))
        #     ).add_to(mc)

        for i in range(0, len(df)):
            #     date = '2024-07-30 17:15:00.000000'
            #     parsed = pendulum.parse(date)
            #     st.write(pendulum.now())
            #     # subtract
            #     difference = pendulum.now() - parsed
            #     st.write(difference.total_seconds())

            date = df.iloc[i]["date_obs"]
            # 2024-07-30 17:15:00.000000
            # parsed = pendulum.from_timestamp(date)
            # difference = pendulum.now() - parsed

            # radius = 10000
            # folium.Circle(
            #     location=[-27.551667, -48.478889],
            #     radius=radius,
            #     color="black",
            #     weight=1,
            #     fill_opacity=0.6,
            #     opacity=1,
            #     fill_color="green",
            #     fill=False,  # gets overridden by fill_color
            #     popup="{} meters".format(radius),
            #     tooltip="I am in meters",
            # ).add_to(m)

            folium.CircleMarker(
                location=[df.iloc[i]["latitude"], df.iloc[i]["longitude"]],
                radius=df.iloc[i]["flood_indicateur"] * 10,
                color="green",
                weight=50,
                opacity=0.3,
                fill_opacity=1,
                fill_color=("red" if df.iloc[i]["flood_indicateur"] > 0.9 else "blue"),
                # icon=folium.Icon(
                # icon="flag",
                fill=False,
                popup=df.iloc[i]["code_station"],
                stroke=True,

            ).add_to(locs_map)

        callback = ('function (row) {'
                    'var circle = L.circle(new L.LatLng(row["latitude"], row["longitude"]), {color: "red",  radius: row["resultat_obs_elab"]});'
                    'return circle};')
        # locs_map.add_child(plugins.FastMarkerCluster(df[['latitude', 'longitude']].values.tolist(), callback=callback))
        st.session_state.map = locs_map
    return st.session_state.map


def create_main_page():
    """
    Creates the following Streamlit headers:
    - A title
    - A subheader
    - A title in the sidebar
    - A markdown section in the sidebar
    """
    # st.image("dashboards/images/BlueRiver.jpg")
    st.logo("dashboards/images/BlueRiver.png")
    start_time = timer()
    credentials = get_service_account_credentials()
    client = get_client(credentials)
    st.title("River flood")
    df = get_historical_data(client)

    st.write(df.head())
    locs_map = get_map(df)
    # # Print results.
    # st_data = folium_static(locs_map, width = 725)
    st_data = st_folium(locs_map, width=725)
    end_time = timer()
    st.write(f"this took {end_time - start_time}")
    st.write(f"site station set to {st_data['last_object_clicked_popup']}")

    # # return

    st.session_state.site_station = st_data["last_object_clicked_popup"]
    return


if __name__ == "__main__":
    create_main_page()
