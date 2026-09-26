import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from googleapiclient.discovery import build
import re
import io
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors as rl_colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


# ---------------- CONFIG ---------------- #

load_dotenv()

API_KEY = os.getenv("API_KEY")

if not API_KEY:
    try:
        API_KEY = st.secrets["API_KEY"]
    except Exception:
        API_KEY = None

if not API_KEY:
    st.error(
        "❌ YouTube API key is missing. "
        "Please configure API_KEY in your .env file or Streamlit Secrets."
    )
    st.stop()

youtube = build("youtube", "v3", developerKey=API_KEY, cache_discovery=False)

st.set_page_config(
    page_title="YouTube Analytics Ultimate",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

CACHE_TTL = 1800  # 30 minutes - saves API quota on repeat lookups

analyzer = SentimentIntensityAnalyzer()


# ---------------- STYLING ---------------- #

def inject_custom_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

        html, body, [class*="css"]  {
            font-family: 'Poppins', sans-serif;
        }

        /* Gradient hero title */
        .hero-title {
            background: linear-gradient(90deg, #FF4B4B 0%, #7C3AED 50%, #4B8BFF 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 2.6rem;
            font-weight: 700;
            margin-bottom: 0;
        }
        .hero-subtitle {
            color: #808495;
            font-size: 1rem;
            margin-top: -0.3rem;
            margin-bottom: 1.2rem;
        }

        /* Metric cards */
        div[data-testid="stMetric"] {
            background: linear-gradient(145deg, #ffffff, #f3f4f8);
            border: 1px solid rgba(124, 58, 237, 0.12);
            border-radius: 14px;
            padding: 14px 16px 10px 16px;
            box-shadow: 0 2px 10px rgba(30, 30, 60, 0.06);
        }
        div[data-testid="stMetric"] label {
            font-weight: 600;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px 10px 0 0;
            padding: 8px 16px;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(90deg, rgba(124,58,237,0.12), rgba(75,139,255,0.12));
        }

        /* Buttons */
        .stButton > button, .stDownloadButton > button {
            border-radius: 10px;
            font-weight: 600;
            border: 1px solid rgba(124, 58, 237, 0.25);
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            border-color: #7C3AED;
            color: #7C3AED;
        }

        /* Expanders */
        details {
            border-radius: 10px !important;
        }

        /* Grade badge */
        .grade-badge {
            display: inline-block;
            font-size: 2.2rem;
            font-weight: 700;
            padding: 6px 22px;
            border-radius: 14px;
            color: white;
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero_header(title, subtitle):
    st.markdown(f'<div class="hero-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hero-subtitle">{subtitle}</div>', unsafe_allow_html=True)


# ---------------- CACHED API CALLS ---------------- #

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def search_channel(query):
    return youtube.search().list(
        part="snippet", q=query, type="channel", maxResults=1
    ).execute()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def search_video(query):
    return youtube.search().list(
        part="snippet", q=query, type="video", maxResults=1
    ).execute()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_channel_data(channel_id):
    return youtube.channels().list(
        part="snippet,statistics,brandingSettings", id=channel_id
    ).execute()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_videos(channel_id, max_results=50):
    return youtube.search().list(
        part="snippet", channelId=channel_id, maxResults=max_results, order="date"
    ).execute()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_video_stats(video_ids_tuple):
    return youtube.videos().list(
        part="statistics,snippet,topicDetails,contentDetails",
        id=",".join(video_ids_tuple)
    ).execute()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_video_comments(video_id, max_results=100):
    try:
        return youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            order="relevance",
            textFormat="plainText",
        ).execute()
    except Exception:
        return None


# ---------------- HELPERS ---------------- #

def get_thumbnail(snippet):
    thumbs = snippet.get("thumbnails", {})
    return (
        thumbs.get("high", {}).get("url")
        or thumbs.get("medium", {}).get("url")
        or thumbs.get("default", {}).get("url")
    )


def extract_links(text):
    url_pattern = re.compile(r'(https?://[^\s\)\]\>\"\']+)')
    return url_pattern.findall(text)


def extract_video_id_from_url(text):
    """If the input looks like a YouTube URL, pull out the video id."""
    patterns = [
        r"(?:v=|/videos/|embed/|youtu\.be/|/v/|/shorts/)([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1)
    return None


def parse_iso8601_duration(duration_str):
    if not duration_str:
        return 0
    pattern = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
    match = pattern.match(duration_str)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def format_duration(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}h {m}m {s}s"
    elif m:
        return f"{m}m {s}s"
    return f"{s}s"


def process_video_data(response):
    data = []
    for item in response.get("items", []):
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})
        content_details = item.get("contentDetails", {})

        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))
        duration_sec = parse_iso8601_duration(content_details.get("duration", ""))

        data.append({
            "video_id": item.get("id"),
            "title": snippet.get("title", "N/A"),
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement": (likes + comments) / views if views else 0,
            "published": snippet.get("publishedAt"),
            "thumbnail": get_thumbnail(snippet),
            "duration_sec": duration_sec,
            "is_short": duration_sec > 0 and duration_sec <= 60,
        })

    df = pd.DataFrame(data)
    if not df.empty:
        df["published"] = pd.to_datetime(df["published"])
        df["day_of_week"] = df["published"].dt.day_name()
        df["hour"] = df["published"].dt.hour

    return df


def show_thumbnail_grid(df_subset, label):
    st.markdown(f"#### {label}")
    cols = st.columns(len(df_subset))
    for col, (_, row) in zip(cols, df_subset.iterrows()):
        with col:
            if row.get("thumbnail"):
                st.image(row["thumbnail"], use_container_width=True)
            title_short = row["title"][:40] + "…" if len(row["title"]) > 40 else row["title"]
            st.caption(f"**{title_short}**")
            st.caption(f"👁 {row['views']:,}  |  👍 {row['likes']:,}")


def export_buttons(df, base_filename):
    """CSV + Excel download buttons for any dataframe."""
    export_df = df.drop(columns=["thumbnail"], errors="ignore")
    col1, col2 = st.columns(2)

    with col1:
        csv_bytes = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV", csv_bytes, file_name=f"{base_filename}.csv",
            mime="text/csv", key=f"csv_{base_filename}"
        )

    with col2:
        # Excel can't store timezone-aware datetimes, so strip tz info
        # from any datetime columns before writing (CSV export above is unaffected).
        excel_df = export_df.copy()
        for col in excel_df.columns:
            if pd.api.types.is_datetime64_any_dtype(excel_df[col]):
                if excel_df[col].dt.tz is not None:
                    excel_df[col] = excel_df[col].dt.tz_localize(None)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            excel_df.to_excel(writer, index=False, sheet_name="Data")
        st.download_button(
            "⬇️ Download Excel", buffer.getvalue(), file_name=f"{base_filename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"xlsx_{base_filename}"
        )


def render_wordcloud(titles):
    text = " ".join(titles)
    if not text.strip():
        st.info("Not enough title text to build a word cloud.")
        return
    wc = WordCloud(
        width=1000, height=450, background_color="white",
        stopwords=STOPWORDS, colormap="viridis"
    ).generate(text)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    st.pyplot(fig)


def render_posting_schedule(df):
    order_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = df.pivot_table(
        index="day_of_week", columns="hour", values="views",
        aggfunc="count", fill_value=0
    ).reindex(order_days)

    st.plotly_chart(
        px.imshow(
            pivot, aspect="auto",
            labels=dict(x="Hour of Day (UTC)", y="Day of Week", color="Videos Posted"),
            title="Upload Schedule Heatmap (video count)"
        ),
        use_container_width=True
    )


def best_time_to_post(df):
    by_hour = df.groupby("hour")["views"].mean().sort_values(ascending=False)
    by_day = df.groupby("day_of_week")["views"].mean().sort_values(ascending=False)

    best_hour = by_hour.index[0] if not by_hour.empty else None
    best_day = by_day.index[0] if not by_day.empty else None

    if best_hour is not None and best_day is not None:
        st.success(
            f"⏰ Historically, videos posted on **{best_day}** around "
            f"**{best_hour}:00 UTC** get the most views on this channel "
            f"(avg {int(by_day.iloc[0]):,} views on {best_day}, "
            f"{int(by_hour.iloc[0]):,} views around {best_hour}:00)."
        )


def render_shorts_split(df):
    counts = df["is_short"].value_counts()
    labels = ["Shorts (≤60s)" if k else "Long-form" for k in counts.index]

    st.plotly_chart(
        px.pie(names=labels, values=counts.values, title="Shorts vs Long-form Videos"),
        use_container_width=True
    )

    avg_by_type = df.groupby("is_short")["views"].mean()
    for is_short, avg in avg_by_type.items():
        label = "Shorts" if is_short else "Long-form"
        st.write(f"- Avg views for **{label}**: {int(avg):,}")


def analyze_comment_sentiment(comments_response):
    rows = []
    for item in comments_response.get("items", []):
        snippet = item["snippet"]["topLevelComment"]["snippet"]
        text = snippet.get("textOriginal", "")
        likes = snippet.get("likeCount", 0)
        score = analyzer.polarity_scores(text)["compound"]

        if score >= 0.05:
            label = "Positive"
        elif score <= -0.05:
            label = "Negative"
        else:
            label = "Neutral"

        rows.append({
            "comment": text,
            "likes": likes,
            "sentiment": label,
            "score": score,
        })

    return pd.DataFrame(rows)


def fetch_channel_summary(channel_name):
    """Used by Compare Channels mode. Returns a dict of key stats, or None."""
    search = search_channel(channel_name)
    if not search.get("items"):
        return None
    channel_id = search["items"][0]["snippet"]["channelId"]

    channel = get_channel_data(channel_id)
    if not channel.get("items"):
        return None

    snippet = channel["items"][0]["snippet"]
    stats = channel["items"][0]["statistics"]

    videos = get_videos(channel_id, max_results=25)
    video_ids = [v["id"]["videoId"] for v in videos.get("items", []) if "videoId" in v["id"]]

    avg_views, avg_engagement = None, None
    if video_ids:
        vdf = process_video_data(get_video_stats(tuple(video_ids)))
        if not vdf.empty:
            avg_views = vdf["views"].mean()
            avg_engagement = vdf["engagement"].mean()

    return {
        "Channel": snippet.get("title", "N/A"),
        "Subscribers": int(stats.get("subscriberCount", 0)),
        "Total Views": int(stats.get("viewCount", 0)),
        "Total Videos": int(stats.get("videoCount", 0)),
        "Avg Views (recent 25)": int(avg_views) if avg_views is not None else None,
        "Avg Engagement (recent 25)": round(avg_engagement, 4) if avg_engagement is not None else None,
        "thumbnail": get_thumbnail(snippet),
    }


def fetch_video_summary(query):
    """Used by Compare Videos mode. Returns a dict of key stats, or None."""
    video_id = extract_video_id_from_url(query)
    if not video_id:
        search = search_video(query)
        if not search.get("items"):
            return None
        video_id = search["items"][0]["id"]["videoId"]

    video = get_video_stats((video_id,))
    if not video.get("items"):
        return None

    item = video["items"][0]
    stats = item.get("statistics", {})
    snippet = item.get("snippet", {})
    content_details = item.get("contentDetails", {})

    views = int(stats.get("viewCount", 0))
    likes = int(stats.get("likeCount", 0))
    comments = int(stats.get("commentCount", 0))
    duration_sec = parse_iso8601_duration(content_details.get("duration", ""))

    return {
        "Title": snippet.get("title", "N/A")[:60],
        "Channel": snippet.get("channelTitle", "N/A"),
        "Views": views,
        "Likes": likes,
        "Comments": comments,
        "Engagement Rate": round((likes + comments) / views, 4) if views else 0,
        "Duration": format_duration(duration_sec),
        "thumbnail": get_thumbnail(snippet),
    }


# ---------------- ADVANCED ANALYTICS ---------------- #

def compute_health_score(df, avg_engagement, consistency, avg_views):
    """
    Composite 0-100 'Channel Health Score' blending engagement, growth
    momentum, and upload consistency into a single interview-friendly KPI.
    """
    # Engagement component (40%) - engagement rate of 0.10+ maxes this out
    engagement_score = min(avg_engagement / 0.10, 1.0) * 40

    # Growth component (35%) - recent 10 vs older 10 videos
    df_sorted = df.sort_values("published")
    recent = df_sorted.tail(10)["views"].mean()
    old = df_sorted.head(10)["views"].mean()
    growth_ratio = (recent / old) if old else 1
    growth_score = min(max((growth_ratio - 0.5) / 1.5, 0), 1) * 35

    # Consistency component (25%) - lower relative std dev is better
    cv = (consistency / avg_views) if avg_views else 1
    consistency_score = min(max(1 - (cv / 2), 0), 1) * 25

    total = round(engagement_score + growth_score + consistency_score, 1)

    if total >= 85:
        grade, color = "A+", "#22c55e"
    elif total >= 70:
        grade, color = "A", "#4ade80"
    elif total >= 55:
        grade, color = "B", "#84cc16"
    elif total >= 40:
        grade, color = "C", "#f59e0b"
    else:
        grade, color = "D", "#ef4444"

    return {
        "score": total,
        "grade": grade,
        "color": color,
        "engagement_score": round(engagement_score, 1),
        "growth_score": round(growth_score, 1),
        "consistency_score": round(consistency_score, 1),
    }


def render_health_score(health):
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown(
            f'<div class="grade-badge" style="background:{health["color"]}">'
            f'{health["grade"]}</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"Channel Health Score: **{health['score']} / 100**")

    with col2:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=health["score"],
            title={"text": "Channel Health Score"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": health["color"]},
                "steps": [
                    {"range": [0, 40], "color": "#fee2e2"},
                    {"range": [40, 55], "color": "#fef3c7"},
                    {"range": [55, 70], "color": "#ecfccb"},
                    {"range": [70, 100], "color": "#dcfce7"},
                ],
            },
        ))
        fig.update_layout(height=220, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"Breakdown → Engagement: {health['engagement_score']}/40 · "
        f"Growth momentum: {health['growth_score']}/35 · "
        f"Consistency: {health['consistency_score']}/25"
    )


def forecast_channel_views(df, days_ahead=90):
    """
    Fits a linear trend to cumulative views over time and extrapolates
    forward. A simple, explainable forecast (no black-box black magic) --
    good for demonstrating applied stats without over-claiming precision.
    """
    d = df.sort_values("published").copy()
    d["ordinal"] = d["published"].dt.tz_localize(None).map(datetime.toordinal)
    d["cumulative_views"] = d["views"].cumsum()

    X = d["ordinal"].values
    y = d["cumulative_views"].values

    if len(X) < 3:
        return None

    slope, intercept = np.polyfit(X, y, 1)

    last_ordinal = X.max()
    future_ordinals = np.arange(last_ordinal + 1, last_ordinal + days_ahead + 1)
    future_dates = [datetime.fromordinal(int(o)) for o in future_ordinals]
    future_values = slope * future_ordinals + intercept

    actual_df = pd.DataFrame({
        "date": d["published"].dt.tz_localize(None),
        "cumulative_views": d["cumulative_views"],
        "type": "Actual",
    })
    forecast_df = pd.DataFrame({
        "date": future_dates,
        "cumulative_views": future_values,
        "type": "Forecast",
    })

    combined = pd.concat([actual_df, forecast_df], ignore_index=True)
    projected_gain = int(future_values[-1] - y[-1])

    return combined, projected_gain, slope


def cluster_content_themes(df, n_clusters=4):
    """
    TF-IDF + KMeans over video titles to auto-discover recurring content
    themes and show which themes perform best -- a lightweight, explainable
    unsupervised-ML feature.
    """
    titles = df["title"].fillna("").tolist()
    n_clusters = max(2, min(n_clusters, len(titles) // 3, 6))

    if len(titles) < n_clusters * 2:
        return None

    vectorizer = TfidfVectorizer(stop_words="english", max_features=500, min_df=1)
    X = vectorizer.fit_transform(titles)

    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = km.fit_predict(X)

    terms = np.array(vectorizer.get_feature_names_out())
    order_centroids = km.cluster_centers_.argsort()[:, ::-1]

    cluster_keywords = {}
    for i in range(n_clusters):
        top_terms = terms[order_centroids[i, :5]]
        cluster_keywords[i] = ", ".join(top_terms)

    result = df.copy()
    result["cluster"] = labels
    result["cluster_theme"] = result["cluster"].map(cluster_keywords)

    summary = (
        result.groupby("cluster_theme")
        .agg(videos=("title", "count"), avg_views=("views", "mean"), avg_engagement=("engagement", "mean"))
        .sort_values("avg_views", ascending=False)
        .reset_index()
    )
    summary["avg_views"] = summary["avg_views"].round(0).astype(int)
    summary["avg_engagement"] = summary["avg_engagement"].round(4)

    return result, summary


def detect_anomalies(df, z_threshold=1.5):
    """Flags statistical outlier videos (viral or underperforming) via z-score."""
    d = df.copy()
    mean_v, std_v = d["views"].mean(), d["views"].std()

    if not std_v:
        d["anomaly"] = "Normal"
        return d

    d["z_score"] = (d["views"] - mean_v) / std_v
    d["anomaly"] = d["z_score"].apply(
        lambda z: "🚀 Viral Outlier" if z > z_threshold
        else ("⚠️ Underperformer" if z < -z_threshold else "Normal")
    )
    return d


def generate_pdf_report(channel_title, key_stats, insights, health):
    """Builds a one-page executive summary PDF for stakeholders/portfolio use."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle", parent=styles["Title"], textColor=rl_colors.HexColor("#7C3AED")
    )
    heading_style = ParagraphStyle(
        "HeadingStyle", parent=styles["Heading2"], textColor=rl_colors.HexColor("#4B8BFF")
    )

    elements = [
        Paragraph(f"YouTube Channel Report — {channel_title}", title_style),
        Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y')}", styles["Normal"]),
        Spacer(1, 16),
        Paragraph(f"Channel Health Score: {health['score']}/100 (Grade {health['grade']})", heading_style),
        Spacer(1, 10),
    ]

    table_data = [["Metric", "Value"]] + [[k, v] for k, v in key_stats.items()]
    table = Table(table_data, colWidths=[2.6 * inch, 2.6 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#7C3AED")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.whitesmoke, rl_colors.white]),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 16))

    elements.append(Paragraph("Key Insights", heading_style))
    elements.append(Spacer(1, 6))
    for insight in insights:
        elements.append(Paragraph(f"• {insight}", styles["Normal"]))
        elements.append(Spacer(1, 4))

    doc.build(elements)
    buffer.seek(0)
    return buffer


# ---------------- UI ---------------- #

inject_custom_css()
hero_header(
    "🚀 YouTube Analytics Ultimate Dashboard",
    "Channel & video intelligence — trends, forecasts, sentiment, and content clustering in one place."
)

mode = st.sidebar.selectbox(
    "Mode",
    ["Channel Analysis", "Video Analysis", "Compare Channels", "Compare Videos"]
)


# ================= CHANNEL ANALYSIS ================= #

if mode == "Channel Analysis":

    channel_name = st.sidebar.text_input("Enter Channel Name")

    if st.sidebar.button("Analyze Channel"):
        try:
            search = search_channel(channel_name)
            if not search.get("items"):
                st.error("Channel not found")
                st.stop()

            channel_id = search["items"][0]["snippet"]["channelId"]
            channel = get_channel_data(channel_id)
            if not channel.get("items"):
                st.error("Channel data not found")
                st.stop()

            snippet = channel["items"][0]["snippet"]
            stats = channel["items"][0]["statistics"]
            branding = channel["items"][0].get("brandingSettings", {}).get("channel", {})

            # ---- Channel Header ---- #
            col1, col2 = st.columns([1, 3])
            with col1:
                img = get_thumbnail(snippet)
                if img:
                    st.image(img)
                else:
                    st.warning("No image available")

            with col2:
                st.subheader(snippet.get("title", "N/A"))
                country = snippet.get("country", "N/A")
                created_at_raw = snippet.get("publishedAt", "")

                if created_at_raw:
                    created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                    age_years = (datetime.now(timezone.utc) - created_at).days // 365
                    created_str = created_at.strftime("%B %d, %Y")
                else:
                    created_str = "N/A"
                    age_years = "N/A"

                st.markdown(
                    f"🌍 **Country:** {country}  |  "
                    f"📅 **Created:** {created_str}  |  "
                    f"⏳ **Age:** {age_years} years"
                )

            # ---- Core Stats ---- #
            c1, c2, c3 = st.columns(3)
            c1.metric("Subscribers", f"{int(stats.get('subscriberCount', 0)):,}")
            c2.metric("Total Views", f"{int(stats.get('viewCount', 0)):,}")
            c3.metric("Total Videos", f"{int(stats.get('videoCount', 0)):,}")

            # ---- Channel Overview ---- #
            description = snippet.get("description", "")
            keywords = branding.get("keywords", "")

            with st.expander("📋 Channel Overview", expanded=True):
                if description:
                    st.markdown("**About this channel:**")
                    st.write(description)
                else:
                    st.info("No description available.")

                if keywords:
                    st.markdown("**Channel Keywords:**")
                    kw_list = [
                        k.strip().strip('"')
                        for k in re.split(r'\s+(?=")|(?<=")\s+|,', keywords)
                        if k.strip().strip('"')
                    ]
                    st.write(", ".join(kw_list))

            with st.expander("🔗 Links in Channel Description", expanded=True):
                links = extract_links(description)
                if links:
                    for link in links:
                        st.markdown(f"- [{link}]({link})")
                else:
                    st.info("No links found in the channel description.")

            # ---- Fetch Videos ---- #
            videos = get_videos(channel_id, max_results=50)
            video_ids = [v["id"]["videoId"] for v in videos.get("items", []) if "videoId" in v["id"]][:50]

            if not video_ids:
                st.error("No videos found")
                st.stop()

            df = process_video_data(get_video_stats(tuple(video_ids)))
            if df.empty:
                st.error("No valid data")
                st.stop()

            avg_views = df["views"].mean()
            avg_engagement = df["engagement"].mean()
            consistency = df["views"].std()

            c4, c5, c6 = st.columns(3)
            c4.metric("Avg Views", f"{int(avg_views):,}")
            c5.metric("Avg Engagement", f"{avg_engagement:.4f}")
            c6.metric("Consistency (Std Dev)", f"{int(consistency):,}")

            st.divider()
            health = compute_health_score(df, avg_engagement, consistency, avg_views)
            render_health_score(health)

            tabs = st.tabs([
                "📸 Thumbnails", "📊 Overview", "📈 Graphs",
                "🧩 Content Clusters", "🔮 Forecast", "🧠 Insights"
            ])

            # ---- THUMBNAILS TAB ---- #
            with tabs[0]:
                top5 = df.sort_values("views", ascending=False).head(5)
                bottom5 = df.sort_values("views").head(5)
                show_thumbnail_grid(top5, "🏆 Top 5 Videos by Views")
                st.divider()
                show_thumbnail_grid(bottom5, "📉 Bottom 5 Videos by Views")

            # ---- OVERVIEW TAB ---- #
            with tabs[1]:
                st.subheader("Top Performing Videos")
                top10 = df.sort_values("views", ascending=False).head(10).reset_index(drop=True)
                st.dataframe(top10.drop(columns=["thumbnail"], errors="ignore"))
                export_buttons(top10, "top_performing_videos")

                st.subheader("Worst Performing Videos")
                worst5 = df.sort_values("views").head(5).reset_index(drop=True)
                st.dataframe(worst5.drop(columns=["thumbnail"], errors="ignore"))
                export_buttons(worst5, "worst_performing_videos")

                st.subheader("Full Video Dataset")
                export_buttons(df, "all_channel_videos")

                st.divider()
                st.subheader("🎯 Statistical Anomaly Detection")
                st.caption("Videos flagged by z-score as significantly over- or under-performing vs. the channel average.")
                anomaly_df = detect_anomalies(df)
                flagged = anomaly_df[anomaly_df["anomaly"] != "Normal"].sort_values("z_score", ascending=False)
                if flagged.empty:
                    st.info("No strong statistical outliers detected in this sample.")
                else:
                    st.dataframe(
                        flagged[["title", "views", "z_score", "anomaly"]].reset_index(drop=True),
                        use_container_width=True
                    )

            # ---- GRAPHS TAB ---- #
            with tabs[2]:
                st.subheader("📊 Views Distribution")
                st.plotly_chart(px.histogram(df, x="views", nbins=30, title="Views Distribution"), use_container_width=True)

                st.subheader("📊 Engagement Distribution")
                st.plotly_chart(px.histogram(df, x="engagement", nbins=30, title="Engagement Spread"), use_container_width=True)

                st.subheader("📈 Views vs Likes")
                st.plotly_chart(
                    px.scatter(df, x="views", y="likes", size="comments", hover_name="title", title="Views vs Likes"),
                    use_container_width=True
                )

                st.subheader("📦 Views Box Plot")
                st.plotly_chart(px.box(df, y="views", title="Outlier Detection"), use_container_width=True)

                st.subheader("📅 Views Trend")
                df_sorted = df.sort_values("published")
                st.plotly_chart(
                    px.line(df_sorted, x="published", y="views", hover_name="title", title="Views Over Time"),
                    use_container_width=True
                )

                st.subheader("🔥 Correlation Heatmap")
                corr = df[["views", "likes", "comments", "engagement"]].corr()
                st.plotly_chart(px.imshow(corr, text_auto=True, title="Correlation"), use_container_width=True)

                st.subheader("☁️ Title Word Cloud")
                render_wordcloud(df["title"].tolist())

                st.subheader("🗓️ Upload Schedule")
                render_posting_schedule(df)

                st.subheader("🎬 Shorts vs Long-form")
                render_shorts_split(df)

            # ---- CONTENT CLUSTERS TAB (TF-IDF + KMeans) ---- #
            with tabs[3]:
                st.subheader("🧩 Auto-Detected Content Themes")
                st.caption(
                    "Unsupervised clustering (TF-IDF + KMeans) over video titles — "
                    "groups videos into recurring content themes and ranks them by performance."
                )

                cluster_result = cluster_content_themes(df)
                if cluster_result is None:
                    st.info("Not enough videos to form meaningful content clusters yet.")
                else:
                    clustered_df, cluster_summary = cluster_result

                    st.plotly_chart(
                        px.bar(
                            cluster_summary, x="cluster_theme", y="avg_views",
                            color="cluster_theme", title="Average Views by Content Theme",
                            labels={"cluster_theme": "Theme (top keywords)", "avg_views": "Avg Views"}
                        ),
                        use_container_width=True
                    )

                    st.dataframe(cluster_summary, use_container_width=True)
                    export_buttons(cluster_summary, "content_theme_summary")

                    best_theme = cluster_summary.iloc[0]
                    st.success(
                        f"🏆 Best-performing theme: **{best_theme['cluster_theme']}** "
                        f"(avg {int(best_theme['avg_views']):,} views across {best_theme['videos']} videos)."
                    )

            # ---- FORECAST TAB (linear trend extrapolation) ---- #
            with tabs[4]:
                st.subheader("🔮 Growth Forecast")
                st.caption(
                    "Linear trend fitted on cumulative views over time, extrapolated 90 days forward. "
                    "A transparent, explainable projection — not a black-box model."
                )

                forecast_result = forecast_channel_views(df, days_ahead=90)
                if forecast_result is None:
                    st.info("Not enough historical data points to build a reliable forecast.")
                else:
                    forecast_df, projected_gain, slope = forecast_result

                    st.plotly_chart(
                        px.line(
                            forecast_df, x="date", y="cumulative_views", color="type",
                            title="Cumulative Views: Actual vs 90-Day Forecast",
                            color_discrete_map={"Actual": "#4B8BFF", "Forecast": "#FF4B4B"}
                        ),
                        use_container_width=True
                    )

                    if slope > 0:
                        st.success(
                            f"📈 At the current trend, this channel is projected to gain roughly "
                            f"**{projected_gain:,} views** over the next 90 days."
                        )
                    else:
                        st.warning(
                            "📉 The current trend line is flat or declining — cumulative view "
                            "growth may be slowing based on recent uploads."
                        )

            # ---- INSIGHTS TAB ---- #
            with tabs[5]:
                st.subheader("🧠 Channel Insights")

                best = df.loc[df["views"].idxmax()]
                worst = df.loc[df["views"].idxmin()]

                st.success(f"🏆 Best Video: {best['title'][:60]} ({best['views']:,} views)")
                st.warning(f"📉 Worst Video: {worst['title'][:60]} ({worst['views']:,} views)")

                recent = df.sort_values("published").tail(10)["views"].mean()
                old = df.sort_values("published").head(10)["views"].mean()

                if recent > old:
                    st.success("📈 Channel is growing — recent videos average more views than older ones.")
                else:
                    st.warning("📉 Growth slowing — recent videos average fewer views than older ones.")

                if avg_engagement > 0.1:
                    st.success("🔥 Strong engagement")
                elif avg_engagement > 0.05:
                    st.info("👍 Moderate engagement")
                else:
                    st.warning("⚠️ Low engagement")

                viral = df[df["views"] > avg_views * 2]
                st.write(f"🔥 Viral Videos (2× avg views): **{len(viral)}**")

                if consistency < avg_views:
                    st.info("📊 Consistent performance across videos")
                else:
                    st.warning("📊 Inconsistent performance — high variance between videos")

                st.divider()
                st.subheader("⏰ Best Time to Post")
                best_time_to_post(df)

                st.divider()
                st.write("🎯 **Strategy Tips:**")
                st.write("- Focus on high-performing content types")
                st.write("- Improve weak video thumbnails/titles")

                st.divider()
                st.subheader("📄 Executive Summary Report")
                st.caption("A one-page PDF summary — handy for sharing with stakeholders or a portfolio writeup.")

                report_insights = [
                    f"Channel Health Score: {health['score']}/100 (Grade {health['grade']}).",
                    f"Best video: {best['title'][:60]} ({best['views']:,} views).",
                    f"Worst video: {worst['title'][:60]} ({worst['views']:,} views).",
                    "Channel is growing." if recent > old else "Recent growth has slowed vs older uploads.",
                    f"Average engagement rate: {avg_engagement:.4f}.",
                    f"{len(viral)} video(s) performed at 2x+ the channel's average views.",
                ]
                report_stats = {
                    "Subscribers": f"{int(stats.get('subscriberCount', 0)):,}",
                    "Total Views": f"{int(stats.get('viewCount', 0)):,}",
                    "Total Videos": f"{int(stats.get('videoCount', 0)):,}",
                    "Avg Views (sample)": f"{int(avg_views):,}",
                    "Avg Engagement": f"{avg_engagement:.4f}",
                    "Consistency (Std Dev)": f"{int(consistency):,}",
                }

                pdf_buffer = generate_pdf_report(
                    snippet.get("title", "N/A"), report_stats, report_insights, health
                )
                st.download_button(
                    "📄 Download Executive Summary (PDF)",
                    data=pdf_buffer,
                    file_name=f"{snippet.get('title', 'channel')}_report.pdf",
                    mime="application/pdf",
                )

        except Exception as e:
            st.error(f"❌ Error: {e}")


# ================= VIDEO ANALYSIS ================= #

elif mode == "Video Analysis":

    video_title = st.sidebar.text_input("Enter Video Title or URL")

    if st.sidebar.button("Analyze Video"):
        try:
            video_id = extract_video_id_from_url(video_title)
            if not video_id:
                search = search_video(video_title)
                if not search.get("items"):
                    st.error("Video not found")
                    st.stop()
                video_id = search["items"][0]["id"]["videoId"]

            video = get_video_stats((video_id,))
            if not video.get("items"):
                st.error("Video data not found")
                st.stop()

            item = video["items"][0]
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            content_details = item.get("contentDetails", {})

            col1, col2 = st.columns([1, 3])
            with col1:
                img = get_thumbnail(snippet)
                if img:
                    st.image(img)
                else:
                    st.warning("No image available")

            with col2:
                st.subheader(snippet.get("title", "N/A"))
                channel_title = snippet.get("channelTitle", "N/A")
                published_raw = snippet.get("publishedAt", "")

                if published_raw:
                    published_dt = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
                    days_since = (datetime.now(timezone.utc) - published_dt).days
                    published_str = published_dt.strftime("%B %d, %Y")
                else:
                    published_str = "N/A"
                    days_since = None

                st.markdown(f"📺 **Channel:** {channel_title}")
                st.markdown(
                    f"📅 **Published:** {published_str}"
                    + (f"  |  ⏳ **{days_since} days ago**" if days_since is not None else "")
                )

                duration_iso = content_details.get("duration", "")
                duration_sec = parse_iso8601_duration(duration_iso)
                if duration_sec:
                    st.markdown(f"⏱️ **Duration:** {format_duration(duration_sec)}")

                definition = content_details.get("definition", "").upper()
                caption = content_details.get("caption", "false")
                if definition:
                    st.markdown(
                        f"🎥 **Quality:** {definition}  |  "
                        f"💬 **Captions:** {'Yes' if caption == 'true' else 'No'}"
                    )

            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))

            engagement = (likes + comments) / views if views else 0
            like_rate = likes / views if views else 0
            comment_rate = comments / views if views else 0
            like_comment_ratio = likes / comments if comments else 0
            views_per_day = views / days_since if days_since and days_since > 0 else None

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Views", f"{views:,}")
            c2.metric("Likes", f"{likes:,}")
            c3.metric("Comments", f"{comments:,}")
            c4.metric("Engagement Rate", f"{engagement:.4f}")

            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Like Rate", f"{like_rate:.2%}")
            c6.metric("Comment Rate", f"{comment_rate:.4%}")
            c7.metric("Like/Comment Ratio", f"{like_comment_ratio:.2f}")
            if views_per_day:
                c8.metric("Avg Views/Day", f"{int(views_per_day):,}")

            description = snippet.get("description", "")
            links = extract_links(description)
            if links:
                with st.expander("🔗 Links in Video Description"):
                    for link in links:
                        st.markdown(f"- [{link}]({link})")

            tags = snippet.get("tags", [])
            if tags:
                with st.expander(f"🏷️ Tags ({len(tags)} total)"):
                    st.write(", ".join(tags))

            tabs = st.tabs(["📊 Graphs", "📈 Advanced Stats", "💬 Sentiment", "🧠 Insights"])

            # ---- GRAPHS TAB ---- #
            with tabs[0]:
                st.subheader("📊 Performance Comparison")
                df_bar = pd.DataFrame({"Metric": ["Views", "Likes", "Comments"], "Count": [views, likes, comments]})
                st.plotly_chart(px.bar(df_bar, x="Metric", y="Count", color="Metric", title="Performance Overview"), use_container_width=True)

                st.subheader("📊 Engagement Breakdown")
                st.plotly_chart(px.pie(df_bar, names="Metric", values="Count", title="Distribution of Interactions"), use_container_width=True)

                st.subheader("⚡ Engagement Rates")
                col_g1, col_g2 = st.columns(2)

                with col_g1:
                    fig_gauge1 = go.Figure(go.Indicator(
                        mode="gauge+number", value=like_rate * 100,
                        title={"text": "Like Rate (%)"},
                        gauge={
                            "axis": {"range": [0, 10]}, "bar": {"color": "#FF4B4B"},
                            "steps": [
                                {"range": [0, 2], "color": "#ffe0e0"},
                                {"range": [2, 5], "color": "#ffb3b3"},
                                {"range": [5, 10], "color": "#ff6666"},
                            ],
                            "threshold": {"line": {"color": "red", "width": 4}, "thickness": 0.75, "value": 4},
                        }
                    ))
                    st.plotly_chart(fig_gauge1, use_container_width=True)

                with col_g2:
                    fig_gauge2 = go.Figure(go.Indicator(
                        mode="gauge+number", value=engagement * 100,
                        title={"text": "Engagement Rate (%)"},
                        gauge={
                            "axis": {"range": [0, 20]}, "bar": {"color": "#4B8BFF"},
                            "steps": [
                                {"range": [0, 5], "color": "#e0eaff"},
                                {"range": [5, 10], "color": "#b3c9ff"},
                                {"range": [10, 20], "color": "#668aff"},
                            ],
                            "threshold": {"line": {"color": "blue", "width": 4}, "thickness": 0.75, "value": 10},
                        }
                    ))
                    st.plotly_chart(fig_gauge2, use_container_width=True)

            # ---- ADVANCED STATS TAB ---- #
            with tabs[1]:
                st.subheader("📈 Derived Statistics")
                derived_data = {
                    "Metric": [
                        "Views", "Likes", "Comments", "Like Rate (per 100 views)",
                        "Comment Rate (per 1000 views)", "Like / Comment Ratio",
                        "Engagement Rate", "Avg Views per Day", "Video Duration", "Days Since Published"
                    ],
                    "Value": [
                        f"{views:,}", f"{likes:,}", f"{comments:,}",
                        f"{like_rate * 100:.2f}%", f"{comment_rate * 1000:.2f}",
                        f"{like_comment_ratio:.2f}", f"{engagement:.4f}",
                        f"{int(views_per_day):,}" if views_per_day else "N/A",
                        format_duration(duration_sec) if duration_sec else "N/A",
                        f"{days_since}" if days_since else "N/A",
                    ]
                }
                derived_df = pd.DataFrame(derived_data)
                st.dataframe(derived_df, use_container_width=True)
                export_buttons(derived_df, "video_derived_stats")

                st.subheader("📉 Interaction Funnel")
                fig_funnel = go.Figure(go.Funnel(
                    y=["Views", "Likes", "Comments"], x=[views, likes, comments],
                    textinfo="value+percent initial",
                    marker={"color": ["#4B8BFF", "#FF4B4B", "#4BFF91"]}
                ))
                fig_funnel.update_layout(title="Viewer Interaction Funnel")
                st.plotly_chart(fig_funnel, use_container_width=True)

                if tags:
                    st.subheader("🏷️ Tag Count Overview")
                    tag_df = pd.DataFrame({"Tag": tags[:20], "Length": [len(t) for t in tags[:20]]})
                    st.plotly_chart(
                        px.bar(tag_df, x="Tag", y="Length", title="Top 20 Tags by Character Length",
                               labels={"Length": "Tag Length (chars)"}),
                        use_container_width=True
                    )

            # ---- SENTIMENT TAB ---- #
            with tabs[2]:
                st.subheader("💬 Comment Sentiment Analysis")

                comments_response = get_video_comments(video_id, max_results=100)

                if not comments_response or not comments_response.get("items"):
                    st.info("No comments available, or comments are disabled for this video.")
                else:
                    sentiment_df = analyze_comment_sentiment(comments_response)

                    if sentiment_df.empty:
                        st.info("No comments could be analyzed.")
                    else:
                        counts = sentiment_df["sentiment"].value_counts()
                        st.plotly_chart(
                            px.pie(
                                names=counts.index, values=counts.values,
                                title=f"Sentiment of Top {len(sentiment_df)} Comments",
                                color=counts.index,
                                color_discrete_map={"Positive": "#4BFF91", "Neutral": "#B0B0B0", "Negative": "#FF4B4B"}
                            ),
                            use_container_width=True
                        )

                        avg_score = sentiment_df["score"].mean()
                        if avg_score > 0.1:
                            st.success(f"🙂 Overall comment sentiment is positive (avg score {avg_score:.2f}).")
                        elif avg_score < -0.1:
                            st.warning(f"🙁 Overall comment sentiment leans negative (avg score {avg_score:.2f}).")
                        else:
                            st.info(f"😐 Overall comment sentiment is fairly neutral (avg score {avg_score:.2f}).")

                        st.markdown("**Top Positive Comments**")
                        for _, row in sentiment_df.sort_values("score", ascending=False).head(3).iterrows():
                            st.write(f"👍 *(score {row['score']:.2f})* {row['comment'][:200]}")

                        st.markdown("**Top Negative Comments**")
                        neg = sentiment_df.sort_values("score").head(3)
                        if neg["score"].max() < -0.05:
                            for _, row in neg.iterrows():
                                st.write(f"👎 *(score {row['score']:.2f})* {row['comment'][:200]}")
                        else:
                            st.write("No strongly negative comments found.")

                        with st.expander("📋 Full Comment Sentiment Table"):
                            st.dataframe(sentiment_df, use_container_width=True)
                            export_buttons(sentiment_df, "comment_sentiment")

            # ---- INSIGHTS TAB ---- #
            with tabs[3]:
                st.subheader("🧠 Video Insights")

                if engagement > 0.1:
                    st.success("🔥 Highly engaging video — exceptional audience interaction!")
                elif engagement > 0.05:
                    st.info("👍 Decent performance — good but room to improve.")
                else:
                    st.warning("📉 Low engagement — the video may need better calls-to-action.")

                if like_rate > 0.05:
                    st.success(f"👍 Strong like rate at {like_rate:.2%} — viewers approve of this content.")
                else:
                    st.warning(f"👍 Like rate is {like_rate:.2%} — consider asking viewers to like.")

                if like_comment_ratio > 10:
                    st.info(f"💬 Like/Comment ratio is {like_comment_ratio:.1f} — viewers like but don't discuss much.")
                elif like_comment_ratio < 3:
                    st.success("💬 High discussion rate — very engaged community.")
                else:
                    st.info("💬 Balanced interaction between likes and comments.")

                if views_per_day:
                    if views_per_day > 10000:
                        st.success(f"📈 Averaging {int(views_per_day):,} views/day — strong momentum!")
                    elif views_per_day > 1000:
                        st.info(f"📊 Averaging {int(views_per_day):,} views/day — steady growth.")
                    else:
                        st.warning(f"📉 Averaging {int(views_per_day):,} views/day — may benefit from promotion.")

                st.write("🎯 **Tips:**")
                st.write("- Encourage comments with a clear question in the video")
                st.write("- Add a strong call-to-action for likes at the video's peak moment")
                st.write("- Optimize title & thumbnail for better CTR")

                if tags:
                    st.write(f"- Video has {len(tags)} tags — ensure they're highly relevant and specific")
                else:
                    st.write("- No tags found — adding relevant tags can improve discoverability")

        except Exception as e:
            st.error(f"❌ Error: {e}")


# ================= COMPARE CHANNELS ================= #

elif mode == "Compare Channels":

    st.sidebar.write("Enter up to 5 channel names, one per line:")
    raw_input = st.sidebar.text_area("Channel Names", height=140)

    if st.sidebar.button("Compare Channels"):
        names = [n.strip() for n in raw_input.splitlines() if n.strip()][:5]

        if len(names) < 2:
            st.error("Please enter at least 2 channel names (one per line).")
            st.stop()

        try:
            summaries = []
            with st.spinner("Fetching channel data..."):
                for name in names:
                    summary = fetch_channel_summary(name)
                    if summary:
                        summaries.append(summary)
                    else:
                        st.warning(f"⚠️ Could not find channel: {name}")

            if not summaries:
                st.error("No valid channels found.")
                st.stop()

            comp_df = pd.DataFrame(summaries)

            st.subheader("📋 Channel Thumbnails")
            cols = st.columns(len(summaries))
            for col, s in zip(cols, summaries):
                with col:
                    if s.get("thumbnail"):
                        st.image(s["thumbnail"], use_container_width=True)
                    st.caption(f"**{s['Channel']}**")

            st.subheader("📊 Comparison Table")
            display_df = comp_df.drop(columns=["thumbnail"])
            st.dataframe(display_df, use_container_width=True)
            export_buttons(display_df, "channel_comparison")

            st.subheader("📈 Subscribers")
            st.plotly_chart(px.bar(comp_df, x="Channel", y="Subscribers", color="Channel"), use_container_width=True)

            st.subheader("📈 Total Views")
            st.plotly_chart(px.bar(comp_df, x="Channel", y="Total Views", color="Channel"), use_container_width=True)

            st.subheader("📈 Total Videos")
            st.plotly_chart(px.bar(comp_df, x="Channel", y="Total Videos", color="Channel"), use_container_width=True)

            if comp_df["Avg Views (recent 25)"].notna().any():
                st.subheader("📈 Avg Views (recent 25 videos)")
                st.plotly_chart(
                    px.bar(comp_df, x="Channel", y="Avg Views (recent 25)", color="Channel"),
                    use_container_width=True
                )

            if comp_df["Avg Engagement (recent 25)"].notna().any():
                st.subheader("📈 Avg Engagement (recent 25 videos)")
                st.plotly_chart(
                    px.bar(comp_df, x="Channel", y="Avg Engagement (recent 25)", color="Channel"),
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"❌ Error: {e}")


# ================= COMPARE VIDEOS ================= #

elif mode == "Compare Videos":

    st.sidebar.write("Enter up to 5 video titles or URLs, one per line:")
    raw_input = st.sidebar.text_area("Video Titles / URLs", height=140)

    if st.sidebar.button("Compare Videos"):
        queries = [q.strip() for q in raw_input.splitlines() if q.strip()][:5]

        if len(queries) < 2:
            st.error("Please enter at least 2 videos (one per line).")
            st.stop()

        try:
            summaries = []
            with st.spinner("Fetching video data..."):
                for q in queries:
                    summary = fetch_video_summary(q)
                    if summary:
                        summaries.append(summary)
                    else:
                        st.warning(f"⚠️ Could not find video: {q}")

            if not summaries:
                st.error("No valid videos found.")
                st.stop()

            comp_df = pd.DataFrame(summaries)

            st.subheader("🖼️ Thumbnails")
            cols = st.columns(len(summaries))
            for col, s in zip(cols, summaries):
                with col:
                    if s.get("thumbnail"):
                        st.image(s["thumbnail"], use_container_width=True)
                    st.caption(f"**{s['Title']}**")

            st.subheader("📊 Comparison Table")
            display_df = comp_df.drop(columns=["thumbnail"])
            st.dataframe(display_df, use_container_width=True)
            export_buttons(display_df, "video_comparison")

            st.subheader("📈 Views")
            st.plotly_chart(px.bar(comp_df, x="Title", y="Views", color="Title"), use_container_width=True)

            st.subheader("📈 Likes")
            st.plotly_chart(px.bar(comp_df, x="Title", y="Likes", color="Title"), use_container_width=True)

            st.subheader("📈 Comments")
            st.plotly_chart(px.bar(comp_df, x="Title", y="Comments", color="Title"), use_container_width=True)

            st.subheader("📈 Engagement Rate")
            st.plotly_chart(px.bar(comp_df, x="Title", y="Engagement Rate", color="Title"), use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error: {e}")
