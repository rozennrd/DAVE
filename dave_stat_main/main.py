import pandas as pd
import utils

if __name__ == "__main__":
    # Charger le CSV
    # df1=pd.read_csv("data/captured_data_2025-02-11 17h42m12s.csv")
    # df2 = pd.read_csv("data/captured_data_2025-03-14 16h40m34s.csv")
    # df3 = pd.read_csv("data/captured_data_2025-03-31 11h30m19s.csv")
    # df = pd.concat([df1, df2, df3], ignore_index=True)
    # df = pd.read_csv("data/Mars_Avril.csv")
    df = pd.read_csv("data/captured_data_2025-05-02 10_55_30.csv")
    
    # Afficher la matrice des coefficients de Pearson
    utils.pearson_correlation(df)

    # Supprimer les nans
    df = df.dropna()

    # # utils.hist_distribution(df)

    # # # Convertir le timestamp en une variable numérique (nombre de secondes écoulées)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['time_seconds'] = (df['timestamp'] - df['timestamp'].min()).dt.total_seconds()

    # # # Définir les variables explicatives (X) et la cible (y)
    # features = ['temp_degC', 'humidity_air_percent', 'light_intensity_baseline', 'light_intensity_stressor', 'soil_moisture']
    features_baseline = ['temp_degC', 'humidity_air_percent', 'light_intensity_baseline', 'soil_moisture']
    # # features_stress = ['temp_degC', 'humidity_air_percent', 'light_intensity_stressor', 'soil_moisture']
    utils.random_xgb(df, features_baseline, 'chan1_voltage_V')
    utils.random_xgb(df, features_baseline, 'chan2_voltage_V')
    utils.random_xgb(df, features_baseline, 'chan3_voltage_V')
    utils.random_xgb(df, features_baseline, 'chan4_voltage_V')