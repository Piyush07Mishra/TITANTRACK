import pandas as pd
from pathlib import Path

forecast_file = Path('equipment_demand_forecast.csv')
if forecast_file.exists():
    df = pd.read_csv(forecast_file)
    print('Forecast data loaded')
    print(f'Equipment types: {sorted(df["equipment_type"].unique())}')

    for eq_type in sorted(df['equipment_type'].unique()):
        eq_data = df[df['equipment_type'] == eq_type]
        print(f'\n=== {eq_type} ===')
        print(f'Weeks: {len(eq_data)}')
        print(f'Total actual: {eq_data["target_checkout_count"].sum()}')
        print(f'Total predicted: {eq_data["predicted_demand"].sum():.1f}')
        print(f'Max actual: {eq_data["target_checkout_count"].max()}')
        print(f'Max predicted: {eq_data["predicted_demand"].max():.1f}')
        print(f'Avg actual: {eq_data["target_checkout_count"].mean():.2f}')
        print(f'Avg predicted: {eq_data["predicted_demand"].mean():.2f}')

        # Show peak weeks
        max_actual_idx = eq_data['target_checkout_count'].idxmax()
        max_pred_idx = eq_data['predicted_demand'].idxmax()
        max_actual_week = eq_data.loc[max_actual_idx, 'year_week']
        max_pred_week = eq_data.loc[max_pred_idx, 'year_week']
        print(f'Peak actual week: {max_actual_week}')
        print(f'Peak predicted week: {max_pred_week}')

        print('Sample weeks:')
        sample = eq_data[['year_week', 'target_checkout_count', 'predicted_demand']].head(5)
        for _, row in sample.iterrows():
            print(f'  {row["year_week"]}: Actual={int(row["target_checkout_count"])}, Predicted={row["predicted_demand"]:.1f}')
else:
    print('Forecast file not found')