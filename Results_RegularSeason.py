import pandas as pd

# Load CSV
matchups = pd.read_csv('data/Matchups_AllYears.CSV')

# Filter regular season (weeks 1-11)
regular_season = matchups[(matchups['IsRegularSeason'] == True) & (matchups['Week'].between(1, 11))]
regular_season = regular_season[~((regular_season['PointsFor'] == 0) & (regular_season['PointsAgainst'] == 0))]

# Compute outcomes
regular_season['Win'] = regular_season['PointsFor'] > regular_season['PointsAgainst']
regular_season['Loss'] = regular_season['PointsFor'] < regular_season['PointsAgainst']
regular_season['Tie'] = (regular_season['PointsFor'] == regular_season['PointsAgainst']) & (regular_season['PointsFor'] > 0)

# Sort by Year, League, Week to prepare for cumulative metrics
regular_season = regular_season.sort_values(['Year','LeagueID','Week','OwnerID'])

# Cumulative team metrics by week
weekly_metrics = regular_season.groupby(['Year','LeagueID','LeagueName','OwnerID','OwnerName','Week']).agg(
    Wins=('Win','sum'),
    Losses=('Loss','sum'),
    Ties=('Tie','sum'),
    PointsFor=('PointsFor','sum'),
    PointsAgainst=('PointsAgainst','sum')
).groupby(level=[0,1,2,3,4]).cumsum().reset_index()

# Games played and averages
weekly_metrics['GamesPlayed'] = weekly_metrics['Wins'] + weekly_metrics['Losses'] + weekly_metrics['Ties']
weekly_metrics['WinPct'] = weekly_metrics['Wins'] / weekly_metrics['GamesPlayed']
weekly_metrics['PointDiff'] = weekly_metrics['PointsFor'] - weekly_metrics['PointsAgainst']
weekly_metrics['AvgPointsFor'] = weekly_metrics['PointsFor'] / weekly_metrics['GamesPlayed']
weekly_metrics['AvgPointsAgainst'] = weekly_metrics['PointsAgainst'] / weekly_metrics['GamesPlayed']

# Playoff rank per week (Wins + PointsFor/10000)
weekly_metrics['PlayoffScore'] = weekly_metrics['Wins'] + weekly_metrics['PointsFor']/10000
weekly_metrics['PlayoffRank'] = weekly_metrics.groupby(['Year','LeagueID','Week'])['PlayoffScore']\
                                             .rank(method='min', ascending=False).astype(int)

# Optional: sort nicely
weekly_metrics = weekly_metrics.sort_values(['Year','LeagueName','Week','PlayoffRank'])

# Save for Power BI
results.to_csv('data/Results_RegularSeason.csv', index=False)

print("Weekly metrics with Playoff rank calculated and saved to WeeklyMetrics_RegularSeason.csv")
