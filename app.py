from flask import Flask, render_template, request
import pandas as pd
from datetime import datetime

app = Flask(__name__)

zebet_scrap = pd.read_csv('./Data/ZebetScrap.csv')
team_rugby = pd.read_csv('./Data/TeamRugby.csv')
betclic_scrap_fix = pd.read_csv('./Data/BetClicScrapFix.csv')

current_year = datetime.now().year

class NoDataFoundException(Exception):
    pass

def calculate_year_weight(row_date):
    confrontation_year = pd.to_datetime(row_date).year
    if current_year - confrontation_year <= 20:
        return 0.5  
    elif current_year - confrontation_year <= 40:
        return 0.3  
    else:
        return 0.2  




        

team_rugby['YearWeight'] = team_rugby['date'].apply(calculate_year_weight)

def average_tries_scored(equipe, dataframe):
    team_data = dataframe[dataframe['Team'] == equipe]
    weighted_average = (team_data['TF'] * team_data['YearWeight']).sum() / team_data['YearWeight'].sum()
    return weighted_average

def predict_tries(prob, avg_tries):
    if prob >= 0.5:
        return round(avg_tries * (1 + (prob - 0.5) * 2))
    else:
        return round(avg_tries * (1 - (0.5 - prob) * 2))

def proba_team(equipe, opponent, dataframe):
    win_rows = len(dataframe[(dataframe['Team'] == equipe) & (dataframe['Opponent'] == opponent) & (dataframe['Result'] == "W")])
    total_matches = len(dataframe[(dataframe['Team'] == equipe) & (dataframe['Opponent'] == opponent)])
    return win_rows / total_matches if total_matches != 0 else 0.0

def proba_opponent(equipe, opponent, dataframe):
    loss_rows = len(dataframe[(dataframe['Team'] == equipe) & (dataframe['Opponent'] == opponent) & (dataframe['Result'] == "L")])
    total_matches = len(dataframe[(dataframe['Team'] == equipe) & (dataframe['Opponent'] == opponent)])
    return loss_rows / total_matches if total_matches != 0 else 0.0

def calculate_percentage_chances(equipe1, equipe2, dataframe, zebet_scrap):
    def cote_to_proba(cote):
        return 1 / cote

    exist_in_betclic = (equipe1 in betclic_scrap_fix['Team'].values) and (equipe2 in betclic_scrap_fix['Opponent'].values)
    exist_in_team_rugby = (equipe1 in dataframe['Team'].values) and (equipe2 in dataframe['Opponent'].values)
    

    cote_equipe1_zebet = zebet_scrap[zebet_scrap['Pays Vainqueur'] == equipe1]['Cote vainqueur'].min()
    cote_equipe2_zebet = zebet_scrap[zebet_scrap['Pays Vainqueur'] == equipe2]['Cote vainqueur'].min()

    prob_team1_zebet = cote_to_proba(cote_equipe1_zebet) if cote_equipe1_zebet else 0
    prob_team2_zebet = cote_to_proba(cote_equipe2_zebet) if cote_equipe2_zebet else 0

    if exist_in_betclic and exist_in_team_rugby:
        prob_team1_betclic = proba_team(equipe1, equipe2, betclic_scrap_fix)
        prob_team2_betclic = proba_opponent(equipe1, equipe2, betclic_scrap_fix)

        prob_team1_rugby = proba_team(equipe1, equipe2, dataframe)
        prob_team2_rugby = proba_opponent(equipe1, equipe2, dataframe)

        combined_prob_team1 = 0.35 * prob_team1_betclic + 0.30 * prob_team1_rugby + 0.35 * prob_team1_zebet
        combined_prob_team2 = 0.35 * prob_team2_betclic + 0.30 * prob_team2_rugby + 0.35 * prob_team2_zebet
    elif exist_in_team_rugby:
        prob_team1_rugby = proba_team(equipe1, equipe2, dataframe)
        prob_team2_rugby = proba_opponent(equipe1, equipe2, dataframe)

        combined_prob_team1 = 0.30 * prob_team1_rugby + 0.35 * prob_team1_zebet
        combined_prob_team2 = 0.30 * prob_team2_rugby + 0.35 * prob_team2_zebet
    else:
        return {"team1": 0.5, "team2": 0.5}

    total_prob = combined_prob_team1 + combined_prob_team2
    if total_prob == 0:
        raise NoDataFoundException("No data found for given teams under the specified conditions")

    return {"team1": combined_prob_team1 / total_prob, "team2": combined_prob_team2 / total_prob}

teams = team_rugby['Team'].unique().tolist()


@app.route('/')
def index():
    return render_template('index.html', teams=teams)

@app.route('/results', methods=['POST'])
def predict():
    equipe1 = request.form.get('equipe1')
    equipe2 = request.form.get('equipe2')

    try:
        precipitation_min = float(request.form.get('precipitation-debut'))
    except (ValueError, TypeError):
        precipitation_min = 0.0

    try:
        precipitation_max = float(request.form.get('precipitation-fin'))
    except (ValueError, TypeError):
        precipitation_max = float('inf')

    filtered_team_rugby = team_rugby[(team_rugby['precipitation_mm'] >= precipitation_min) & 
                                     (team_rugby['precipitation_mm'] <= precipitation_max)]
    
 
    temperature_range = request.form.get('meteo')
    if temperature_range == "moins0":
        filtered_team_rugby = filtered_team_rugby[filtered_team_rugby['TranchTemp'] == "moins de 0"]
    elif temperature_range == "0-20":
        filtered_team_rugby = filtered_team_rugby[(filtered_team_rugby['TranchTemp'] == "0-20") | (filtered_team_rugby['TranchTemp'] == "no data")]
    elif temperature_range == "20-30":
        filtered_team_rugby = filtered_team_rugby[filtered_team_rugby['TranchTemp'] == "20-30"]


    wind_range = request.form.get('wind')
    if wind_range == "moins30":
        filtered_team_rugby = filtered_team_rugby[(filtered_team_rugby['TranchWind'] == "moins de 30") | (filtered_team_rugby['TranchWind'] == "no data")]
    elif wind_range == "30-60":
        filtered_team_rugby = filtered_team_rugby[filtered_team_rugby['TranchWind'] == "30-60"]

        
    try:
        results = calculate_percentage_chances(equipe1, equipe2, filtered_team_rugby, zebet_scrap)

        avg_tries_team1 = average_tries_scored(equipe1, filtered_team_rugby)
        avg_tries_team2 = average_tries_scored(equipe2, filtered_team_rugby)
        predicted_tries_team1 = predict_tries(results['team1'], avg_tries_team1)
        predicted_tries_team2 = predict_tries(results['team2'], avg_tries_team2)

        if results['team1'] > results['team2']:
            predicted_winner = equipe1
        elif results['team1'] < results['team2']:
            predicted_winner = equipe2
        else:
            predicted_winner = "Match Nul"
        
        cote_team1 = 1 / results['team1'] if results['team1'] != 0 else float('inf')
        cote_team2 = 1 / results['team2'] if results['team2'] != 0 else float('inf')

        percentage_victoires_equipe1 = results['team1'] * 100
        percentage_victoires_equipe2 = results['team2'] * 100
        percentage_defaites_equipe1 = (1 - results['team1']) * 100
        percentage_defaites_equipe2 = (1 - results['team2']) * 100
        percentage_matchs_nuls_equipe1 = 100 - percentage_victoires_equipe1 - percentage_defaites_equipe1
        percentage_matchs_nuls_equipe2 = 100 - percentage_victoires_equipe2 - percentage_defaites_equipe2

        return render_template('results.html', equipe1=equipe1, equipe2=equipe2, 
                               prob_team1=results['team1'], prob_team2=results['team2'],
                               avg_tries_team1=avg_tries_team1, avg_tries_team2=avg_tries_team2,
                               predicted_tries_team1=predicted_tries_team1, predicted_tries_team2=predicted_tries_team2,
                               cote_equipe1=cote_team1, cote_equipe2=cote_team2,
                               percentage_victoires_equipe1=percentage_victoires_equipe1,
                               percentage_victoires_equipe2=percentage_victoires_equipe2,
                               percentage_defaites_equipe1=percentage_defaites_equipe1,
                               percentage_defaites_equipe2=percentage_defaites_equipe2,
                               percentage_matchs_nuls_equipe1=percentage_matchs_nuls_equipe1,
                               percentage_matchs_nuls_equipe2=percentage_matchs_nuls_equipe2,
                               predicted_winner=predicted_winner)
    except NoDataFoundException:
        return render_template('error.html')



@app.route('/Tournoi', methods=['GET', 'POST'])
@app.route('/ResultTournoi', methods=['GET', 'POST'])
def tournament_simulation():
    if request.method == "POST":
      
        try:
            precipitation_min = float(request.form.get('precipitation-debut'))
        except (ValueError, TypeError):
            precipitation_min = 0.0

        try:
            precipitation_max = float(request.form.get('precipitation-fin'))
        except (ValueError, TypeError):
            precipitation_max = float('inf')

        filtered_team_rugby = team_rugby[(team_rugby['precipitation_mm'] >= precipitation_min) & 
                                         (team_rugby['precipitation_mm'] <= precipitation_max)]
        
        temperature_range = request.form.get('meteo')
        if temperature_range == "moins0":
            filtered_team_rugby = filtered_team_rugby[filtered_team_rugby['TranchTemp'] == "moins de 0"]
        elif temperature_range == "0-20":
            filtered_team_rugby = filtered_team_rugby[(filtered_team_rugby['TranchTemp'] == "0-20") | 
                                                      (filtered_team_rugby['TranchTemp'] == "no data")]
        elif temperature_range == "20-30":
            filtered_team_rugby = filtered_team_rugby[filtered_team_rugby['TranchTemp'] == "20-30"]

        wind_range = request.form.get('wind')
        if wind_range == "moins30":
            filtered_team_rugby = filtered_team_rugby[(filtered_team_rugby['TranchWind'] == "moins de 30") | 
                                                      (filtered_team_rugby['TranchWind'] == "no data")]
        elif wind_range == "30-60":
            filtered_team_rugby = filtered_team_rugby[filtered_team_rugby['TranchWind'] == "30-60"]
        
        
        tournament_results = round_robin_simulation(filtered_team_rugby, zebet_scrap)
        
        return render_template('ResultTournoi.html', results=tournament_results)
    
    return render_template('Tournoi.html')


def round_robin_simulation(dataframe, zebet_scrap):
    team_points = {team: 0 for team in teams}
    for i in range(len(teams)):
        for j in range(i+1, len(teams)):
            team1 = teams[i]
            team2 = teams[j]

            results = calculate_percentage_chances(team1, team2, dataframe, zebet_scrap)
            
            if results['team1'] > results['team2']:
                team_points[team1] += 3
            elif results['team1'] < results['team2']:
                team_points[team2] += 3
            else:
                team_points[team1] += 1
                team_points[team2] += 1
                
    
    sorted_teams = sorted(team_points, key=team_points.get, reverse=True)

    for i in range(len(sorted_teams) - 1):
        if team_points[sorted_teams[i]] == team_points[sorted_teams[i+1]]:
            results = calculate_percentage_chances(sorted_teams[i], sorted_teams[i+1], dataframe, zebet_scrap)
            if results['team1'] < results['team2']:
                sorted_teams[i], sorted_teams[i+1] = sorted_teams[i+1], sorted_teams[i]

   
    results = {}
    total_points = sum(team_points.values())
    for team in sorted_teams:
        prob_of_winning = team_points[team] / total_points
        avg_tries = average_tries_scored(team, dataframe)
        cote = 1 / prob_of_winning if prob_of_winning != 0 else float('inf')
        
        
        results[team] = {
            "points": team_points[team],
            "probability": prob_of_winning,
            "avg_tries": avg_tries,
            "cote": cote
        }
    
    return results




if __name__ == '__main__':
    app.run(debug=True)
