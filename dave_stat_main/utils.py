from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from xgboost import XGBRegressor
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def pearson_correlation(df_file):
    # Sélectionner uniquement les colonnes des channels
    channels = ['chan1_voltage_V', 'chan2_voltage_V', 'chan3_voltage_V', 'chan4_voltage_V']
    df_channels = df_file[channels]

    # Calculer la matrice de corrélation de Pearson
    corr_matrix = df_channels.corr(method='pearson')

    # Afficher le heatmap avec Matplotlib & Seaborn
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", linewidths=0.5)

    # Personnalisation de l'affichage
    plt.title("Matrice de corrélation de Pearson entre les channels")
    plt.xticks(rotation=45)
    plt.yticks(rotation=0)
    plt.show()


def linear_regression(df, features, target):
    X = df[features]
    y = df[target]

    # Standardiser les variables (important pour les modèles linéaires)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Séparer en train/test
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    # Entraîner la régression linéaire multiple
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Faire des prédictions
    y_pred = model.predict(X_test)

    #  Évaluer le modèle
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"📊 Performance du modèle, {target}:")
    print(f"➡ Erreur quadratique moyenne (MSE) : {mse:.5f}")
    print(f"➡ Coefficient de détermination (R²) : {r2:.3f}")

    # Afficher les coefficients du modèle
    coeff_df = pd.DataFrame({'Feature': features, 'Coefficient': model.coef_})
    print(f"🔎 Coefficients du modèle, {target}:")
    print(coeff_df)
    print("\n")
    visualisation_pred_reality_lr(y_test, y_pred, target)

def random_xgb(df, features, target):
    X = df[features]
    y = df[target]

    # Standardiser les variables (important pour XGBoost)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Séparer en train/test
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    # Entraîner un modèle Random Forest
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)

    # Entraîner un modèle XGBoost
    xgb = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42)
    xgb.fit(X_train, y_train)

    # Prédictions
    y_pred_rf = rf.predict(X_test)
    y_pred_xgb = xgb.predict(X_test)

    # Évaluer les modèles
    mse_rf = mean_squared_error(y_test, y_pred_rf)
    r2_rf = r2_score(y_test, y_pred_rf)

    mse_xgb = mean_squared_error(y_test, y_pred_xgb)
    r2_xgb = r2_score(y_test, y_pred_xgb)

    print(f"📊 Performance du modèle Random Forest, {target}:")
    print(f"➡ MSE : {mse_rf:.6f}")
    print(f"➡ R² : {r2_rf:.3f}")

    print(f"\n📊 Performance du modèle XGBoost, {target}:")
    print(f"➡ MSE : {mse_xgb:.6f}")
    print(f"➡ R² : {r2_xgb:.3f}")

    # Importance des variables
    importances_rf = rf.feature_importances_
    importances_xgb = xgb.feature_importances_

    importance_df = pd.DataFrame({'Feature': features, 'Importance_RF': importances_rf, 'Importance_XGB': importances_xgb})
    print(f"\n🔎 Importance des variables, {target} :")
    print(f"{importance_df} \n")
    visualisation_pred_reality_rf(y_test, y_pred_rf, target)
    visualisation_pred_reality_xgb(y_test, y_pred_xgb, target)

def visualisation_pred_reality_lr(y_test, y_pred, target):
    plt.figure(figsize=(8, 5))
    plt.scatter(y_test, y_pred, alpha=0.5)
    plt.xlabel(f"Valeurs réelles ({target})")
    plt.ylabel("Valeurs prédites")
    plt.title("Comparaison entre les prédictions et les valeurs réelles")
    plt.plot([-0.03, 0.03], [-0.03, 0.03], color="red", linestyle="--")  # Ligne y = x pour voir l'alignement parfait
    plt.show()

def visualisation_pred_reality_rf(y_test, y_pred_rf, target):
    plt.figure(figsize=(12,5))
    plt.subplot(1, 2, 1)
    plt.scatter(y_test, y_pred_rf, alpha=0.5, label="Predictions RF")
    plt.xlabel("Valeurs réelles")
    plt.ylabel("Valeurs prédites")
    plt.title(f"Random Forest, {target}: Réel vs Prédit")
    plt.plot([-0.03, 0.03], [-0.03, 0.03], color="red", linestyle="--")  # Ligne y=x
    plt.show()

def visualisation_pred_reality_xgb(y_test, y_pred_xgb, target):
    plt.subplot(1, 2, 2)
    plt.scatter(y_test, y_pred_xgb, alpha=0.5, label="Predictions XGB", color='orange')
    plt.xlabel("Valeurs réelles")
    plt.ylabel("Valeurs prédites")
    plt.title(f"XGBoost, {target} : Réel vs Prédit")
    plt.plot([-0.03, 0.03], [-0.03, 0.03], color="red", linestyle="--")  # Ligne y=x
    plt.show()

def stats_desc(df):
    # Colonnes cibles
    colonnes_cibles = [
        'chan1_voltage_V', 
        'chan2_voltage_V', 
        'chan3_voltage_V', 
        'chan4_voltage_V',
        'temp_degC',
        'humidity_air_percent',
        'light_intensity_baseline',
        'light_intensity_stressor',
        'soil_moisture']
    # Stats descriptives classiques
    desc = df[colonnes_cibles].describe().T
    desc['skew'] = df[colonnes_cibles].skew()
    desc['kurtosis'] = df[colonnes_cibles].kurtosis()

    print(desc)

def hist_distribution(df):
    colonnes_cibles = [
        'chan1_voltage_V', 
        'chan2_voltage_V', 
        'chan3_voltage_V', 
        'chan4_voltage_V',
        'temp_degC',
        'humidity_air_percent',
        'light_intensity_baseline',
        'light_intensity_stressor',
        'soil_moisture']
    # Histogrammes pour voir les distributions
    df[colonnes_cibles].hist(bins=30, figsize=(15, 10), edgecolor='black')
    plt.suptitle("Histogrammes des variables", fontsize=16)
    plt.tight_layout()
    plt.show()

    # Boxplots pour comparer les tensions
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df[['chan1_voltage_V', 'chan2_voltage_V', 'chan3_voltage_V', 'chan4_voltage_V']])
    plt.title("Comparaison des tensions électriques par canal")
    plt.ylabel("Voltage (V)")
    plt.show()
