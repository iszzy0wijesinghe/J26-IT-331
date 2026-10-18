APP_CSS = """
<style>
@import url("https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700;800&display=swap");

:root {
    --navy: #10233A;
    --navy-light: #1C3550;
    --teal: #0F766E;
    --teal-soft: #CCFBF1;
    --canvas: #F4F7FB;
    --surface: #FFFFFF;
    --text: #1E2F41;
    --muted: #5B6F84;
    --border: #D7E1EC;
    --danger: #B42318;
    --warning: #B54708;
    --ok: #067647;
}

html, body, [class*="css"] {
    font-family: "Source Sans 3", "Segoe UI", sans-serif;
}

.stApp {
    background: var(--canvas);
    color: var(--text);
}

[data-testid="stHeader"] {
    background: rgba(244, 247, 251, 0.96);
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #10233A 0%, #16324C 100%);
    border-right: 1px solid #274864;
}

[data-testid="stSidebar"] * {
    color: #E8F0F7;
}

[data-testid="stSidebar"] hr {
    border-color: #38516B;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #C5D4E4;
}

[data-testid="stSidebar"] button {
    background: #203B56;
    border: 1px solid #42617D;
    color: #FFFFFF;
}

[data-testid="stSidebar"] button:hover {
    background: #0F766E;
    border-color: #5EEAD4;
    color: #FFFFFF;
}

.block-container {
    padding-top: 1.6rem;
    padding-bottom: 2.4rem;
    max-width: 1680px;
}

h1, h2, h3, h4 {
    color: #10233A !important;
    letter-spacing: -0.25px;
}

p, li, label {
    color: var(--text);
}

[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 4px 14px rgba(16, 35, 58, 0.04);
}

[data-testid="stMetricLabel"] {
    color: var(--muted) !important;
    font-weight: 600;
}

[data-testid="stMetricValue"] {
    color: var(--navy) !important;
    font-weight: 750;
}

.hero {
    background: linear-gradient(120deg, #10233A 0%, #1C4B63 62%, #0F766E 100%);
    border: 1px solid #31516D;
    border-radius: 18px;
    padding: 26px 28px;
    margin-bottom: 20px;
    box-shadow: 0 10px 26px rgba(16, 35, 58, 0.14);
}

.hero-label {
    color: #99F6E4;
    font-size: 12px;
    font-weight: 750;
    letter-spacing: 1.8px;
    text-transform: uppercase;
}

.hero-title {
    color: #FFFFFF;
    font-size: 30px;
    font-weight: 800;
    margin: 8px 0 6px;
}

.hero-subtitle {
    color: #D7E7F3;
    font-size: 15px;
    line-height: 1.65;
    max-width: 980px;
}

.help-card, .provenance-banner, .empty-card {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px 18px;
    margin-bottom: 16px;
}

.provenance-banner {
    background: #F0FDFA;
    border-color: #99F6E4;
}

.help-card h4, .provenance-banner h4, .empty-card h4 {
    margin: 0 0 8px;
    color: #10233A;
}

.help-card p, .provenance-banner p, .empty-card p {
    margin: 0;
    color: #355068;
    line-height: 1.6;
}

div.stButton > button {
    background: #FFFFFF;
    color: var(--navy);
    border: 1px solid #C9D7E5;
    border-radius: 10px;
    min-height: 42px;
    font-weight: 650;
}

div.stButton > button:hover {
    background: #E6FFFB;
    border-color: var(--teal);
    color: #115E59;
}

[data-testid="stDataFrame"] {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
}

[data-testid="stPlotlyChart"],
[data-testid="stVegaLiteChart"],
[data-testid="stArrowVegaLiteChart"] {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 10px;
}

[data-testid="stAlert"] {
    border-radius: 10px;
}

footer {
    visibility: hidden;
}
</style>
"""
