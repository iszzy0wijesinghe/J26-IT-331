import pandas as pd

df = pd.read_csv(r'c:\Users\User\Desktop\Dataset\all datasets\C4_Trust.csv')

print('=== Dataset Overview ===')
print(f'Shape: {df.shape}')
print(f'\nColumns: {list(df.columns)}')

print('\n=== Label Distribution ===')
print(df['trust_label'].value_counts())
print('\nLabel percentages:')
print(df['trust_label'].value_counts(normalize=True) * 100)

print('\n=== Scenario Distribution ===')
print(df['scenario'].value_counts())

print('\n=== Scenario vs Split Cross-Tabulation ===')
print(pd.crosstab(df['scenario'], df['split'], margins=True))

print('\n=== Device Distribution ===')
print(f'Unique devices: {df["device_id"].nunique()}')
print(df['device_id'].value_counts().head(20))

print('\n=== Security Field Correlation with Trust Label ===')
security_fields = ['cert_registered', 'channel_auth_ok', 'signature_valid',
                   'attestation_passed', 'firmware_approved', 'config_hash_match',
                   'payload_hash_match', 'prev_hash_match', 'path_valid',
                   'provenance_complete', 'hub_match', 'location_match']

for field in security_fields:
    print(f'\n{field}:')
    print(df.groupby('trust_label')[field].value_counts())

print('\n=== Deterministic Leakage Check ===')
print('Checking if label_untrusted_binary is perfectly correlated with security fields...')
for field in security_fields:
    correlation = df[['label_untrusted_binary', field]].corr().iloc[0, 1]
    print(f'{field}: {correlation:.4f}')

print('\n=== Trust Score Distribution by Label ===')
print(df.groupby('trust_label')['c4_trust_score'].describe())

print('\n=== Reason Code Distribution ===')
print(df['reason_code'].value_counts())

print('\n=== Scenario Distribution by Label ===')
print(pd.crosstab(df['scenario'], df['trust_label'], margins=True))
