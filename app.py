import streamlit as st
import pandas as pd   
                                                                                                 
import plotly.express as px                                  
import plotly.graph_objects as go
from googleapiclient.discovery import build
import re
from datetime import datetime, timezone

# ---------------- CONFIG ---------------- #
API_KEY = "AIzaSyACles4MTpe7AMxia8VjkG3tt3yv5DU2sM"
youtube = build('youtube', 'v3', developerKey=API_KEY)

st.set_page_config(page_title="YouTube Analytics Ultimate", layout="wide")

# ---------------- FUNCTIONS ---------------- #

def search_channel(query):
    return youtube.search().list(part="snippet", q=query, type="channel", maxResults=1).execute()

def search_video(query):
    return youtube.search().list(part="snippet", q=query, type="video", maxResults=1).execute()

def get_channel_data(channel_id):
    return youtube.channels().list(part="snippet,statistics,brandingSettings", id=channel_id).execute()

def get_videos(channel_id):
    return youtube.search().list(part="snippet", channelId=channel_id, maxResults=50, order="date").execute()

def get_video_stats(video_ids):
    return youtube.videos().list(part="statistics,snippet,topicDetails,contentDetails", id=",".join(video_ids)).execute()

def get_thumbnail(snippet):
    thumbs = snippet.get('thumbnails', {})
    return (
        thumbs.get('high', {}).get('url') or
        thumbs.get('medium', {}).get('url') or
        thumbs.get('default', {}).get('url')
    )

def extract_links(text):
    """Extract all URLs from a block of text."""
    url_pattern = re.compile(
        r'(https?://[^\s\)\]\>\"\']+)'
    )
    return url_pattern.findall(text)

def process_video_data(response):
    data = []
    for item in response.get('items', []):
        stats = item.get('statistics', {})
        snippet = item.get('snippet', {})

        views = int(stats.get('viewCount', 0))
        likes = int(stats.get('likeCount', 0))
        comments = int(stats.get('commentCount', 0))
        thumb = get_thumbnail(snippet)

        data.append({
            "title": snippet.get('title', 'N/A'),
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement": (likes + comments) / views if views else 0,
            "published": snippet.get('publishedAt'),
            "thumbnail": thumb,
        })

    df = pd.DataFrame(data)
    if not df.empty:
        df['published'] = pd.to_datetime(df['published'])
    return df

def parse_iso8601_duration(duration_str):
    """Convert ISO 8601 duration (PT4M13S) to total seconds."""
    if not duration_str:
        return 0
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
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
    else:
        return f"{s}s"

# -------- THUMBNAIL GRID HELPER -------- #
def show_thumbnail_grid(df_subset, label):
    st.markdown(f"#### {label}")
    cols = st.columns(len(df_subset))
    for col, (_, row) in zip(cols, df_subset.iterrows()):
        with col:
            if row.get('thumbnail'):
                st.image(row['thumbnail'], use_container_width=True)
            title_short = row['title'][:40] + "…" if len(row['title']) > 40 else row['title']
            st.caption(f"**{title_short}**")
            st.caption(f"👁 {row['views']:,}  |  👍 {row['likes']:,}")

# ---------------- UI ---------------- #

st.title("🚀 YouTube Analytics Ultimate Dashboard")

mode = st.sidebar.selectbox("Mode", ["Channel Analysis", "Video Analysis"])

# ================= CHANNEL ================= #
if mode == "Channel Analysis":

    channel_name = st.sidebar.text_input("Enter Channel Name")

    if st.sidebar.button("Analyze Channel"):

        try:
            search = search_channel(channel_name)
            if not search.get('items'):
                st.error("Channel not found")
                st.stop()

            channel_id = search['items'][0]['snippet']['channelId']
            channel = get_channel_data(channel_id)

            snippet = channel['items'][0]['snippet']
            stats = channel['items'][0]['statistics']
            branding = channel['items'][0].get('brandingSettings', {}).get('channel', {})

            # ---- Channel Header ---- #
            col1, col2 = st.columns([1, 3])

            with col1:
                img = get_thumbnail(snippet)
                if img:
                    st.image(img)
                else:
                    st.warning("No image available")

            with col2:
                st.subheader(snippet.get('title', 'N/A'))

                # Country & creation date
                country = snippet.get('country', 'N/A')
                created_at_raw = snippet.get('publishedAt', '')
                if created_at_raw:
                    created_at = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00'))
                    age_years = (datetime.now(timezone.utc) - created_at).days // 365
                    created_str = created_at.strftime("%B %d, %Y")
                else:
                    created_str = "N/A"
                    age_years = "N/A"

                st.markdown(f"🌍 **Country:** {country}  |  📅 **Created:** {created_str}  |  ⏳ **Age:** {age_years} years")

            # ---- Core Stats ---- #
            c1, c2, c3 = st.columns(3)
            c1.metric("Subscribers", f"{int(stats.get('subscriberCount', 0)):,}")
            c2.metric("Total Views", f"{int(stats.get('viewCount', 0)):,}")
            c3.metric("Total Videos", f"{int(stats.get('videoCount', 0)):,}")

            # ---- Channel Overview ---- #
            description = snippet.get('description', '')
            keywords = branding.get('keywords', '')

            with st.expander("📋 Channel Overview", expanded=True):
                if description:
                    st.markdown("**About this channel:**")
                    st.write(description)
                else:
                    st.info("No description available.")

                if keywords:
                    st.markdown("**Channel Keywords:**")
                    kw_list = [k.strip().strip('"') for k in re.split(r'\s+(?=")|(?<=")\s+|,', keywords) if k.strip().strip('"')]
                    st.write(", ".join(kw_list))

            # ---- Links from Description ---- #
            with st.expander("🔗 Links in Channel Description", expanded=True):
                links = extract_links(description)
                if links:
                    for link in links:
                        st.markdown(f"- [{link}]({link})")
                else:
                    st.info("No links found in the channel description.")

            # ---- Fetch Videos ---- #
            videos = get_videos(channel_id)
            video_ids = [v['id']['videoId'] for v in videos.get('items', []) if 'videoId' in v['id']]

            if not video_ids:
                st.error("No videos found")
                st.stop()

            video_ids = video_ids[:50]
            df = process_video_data(get_video_stats(video_ids))

            if df.empty:
                st.error("No valid data")
                st.stop()

            avg_views = df['views'].mean()
            avg_engagement = df['engagement'].mean()
            consistency = df['views'].std()

            c4, c5, c6 = st.columns(3)
            c4.metric("Avg Views", f"{int(avg_views):,}")
            c5.metric("Avg Engagement", f"{avg_engagement:.4f}")
            c6.metric("Consistency (Std Dev)", f"{int(consistency):,}")

            tabs = st.tabs(["📸 Thumbnails", "📊 Overview", "📈 Graphs", "🧠 Insights"])

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
                st.dataframe(
                    df.sort_values("views", ascending=False)
                      .head(10)
                      .drop(columns=["thumbnail"], errors="ignore")
                      .reset_index(drop=True)
                )

                st.subheader("Worst Performing Videos")
                st.dataframe(
                    df.sort_values("views")
                      .head(5)
                      .drop(columns=["thumbnail"], errors="ignore")
                      .reset_index(drop=True)
                )

            # ---- GRAPHS TAB ---- #
            with tabs[2]:
                st.subheader("📊 Views Distribution")
                st.plotly_chart(px.histogram(df, x="views", nbins=30, title="Views Distribution"),
                                use_container_width=True)

                st.subheader("📊 Engagement Distribution")
                st.plotly_chart(px.histogram(df, x="engagement", nbins=30, title="Engagement Spread"),
                                use_container_width=True)

                st.subheader("📈 Views vs Likes")
                st.plotly_chart(px.scatter(df, x="views", y="likes", size="comments",
                                           hover_name="title", title="Views vs Likes"),
                                use_container_width=True)

                st.subheader("📦 Views Box Plot")
                st.plotly_chart(px.box(df, y="views", title="Outlier Detection"),
                                use_container_width=True)

                st.subheader("📅 Views Trend")
                df_sorted = df.sort_values("published")
                st.plotly_chart(px.line(df_sorted, x="published", y="views",
                                        hover_name="title", title="Views Over Time"),
                                use_container_width=True)

                st.subheader("🔥 Correlation Heatmap")
                corr = df[['views', 'likes', 'comments', 'engagement']].corr()
                st.plotly_chart(px.imshow(corr, text_auto=True, title="Correlation"),
                                use_container_width=True)

            # ---- INSIGHTS TAB ---- #
            with tabs[3]:
                st.subheader("🧠 Channel Insights")

                best = df.loc[df['views'].idxmax()]
                worst = df.loc[df['views'].idxmin()]

                st.success(f"🏆 Best Video: {best['title'][:60]} ({best['views']:,} views)")
                st.warning(f"📉 Worst Video: {worst['title'][:60]} ({worst['views']:,} views)")

                recent = df.sort_values("published").tail(10)['views'].mean()
                old = df.sort_values("published").head(10)['views'].mean()

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

                viral = df[df['views'] > avg_views * 2]
                st.write(f"🔥 Viral Videos (2× avg views): **{len(viral)}**")

                if consistency < avg_views:
                    st.info("📊 Consistent performance across videos")
                else:
                    st.warning("📊 Inconsistent performance — high variance between videos")

                st.write("🎯 **Strategy Tips:**")
                st.write("- Focus on high-performing content types")
                st.write("- Improve weak video thumbnails/titles")

        except Exception as e:
            st.error(str(e))

# ================= VIDEO ================= #
elif mode == "Video Analysis":

    video_title = st.sidebar.text_input("Enter Video Title")

    if st.sidebar.button("Analyze Video"):

        try:
            search = search_video(video_title)
            if not search.get('items'):
                st.error("Video not found")
                st.stop()

            video_id = search['items'][0]['id']['videoId']
            video = get_video_stats([video_id])
            item = video['items'][0]

            stats = item.get('statistics', {})
            snippet = item.get('snippet', {})
            content_details = item.get('contentDetails', {})

            # ---- Video Header ---- #
            col1, col2 = st.columns([1, 3])

            with col1:
                img = get_thumbnail(snippet)
                if img:
                    st.image(img)

            with col2:
                st.subheader(snippet.get('title', 'N/A'))
                channel_title = snippet.get('channelTitle', 'N/A')
                published_raw = snippet.get('publishedAt', '')
                if published_raw:
                    published_dt = datetime.fromisoformat(published_raw.replace('Z', '+00:00'))
                    days_since = (datetime.now(timezone.utc) - published_dt).days
                    published_str = published_dt.strftime("%B %d, %Y")
                else:
                    published_str = "N/A"
                    days_since = None

                st.markdown(f"📺 **Channel:** {channel_title}")
                st.markdown(f"📅 **Published:** {published_str}" +
                            (f"  |  ⏳ **{days_since} days ago**" if days_since is not None else ""))

                duration_iso = content_details.get('duration', '')
                duration_sec = parse_iso8601_duration(duration_iso)
                if duration_sec:
                    st.markdown(f"⏱️ **Duration:** {format_duration(duration_sec)}")

                definition = content_details.get('definition', '').upper()
                caption = content_details.get('caption', 'false')
                if definition:
                    st.markdown(f"🎥 **Quality:** {definition}  |  💬 **Captions:** {'Yes' if caption == 'true' else 'No'}")

            # ---- Core Metrics ---- #
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            comments = int(stats.get('commentCount', 0))
            favorites = int(stats.get('favoriteCount', 0))

            engagement = (likes + comments) / views if views else 0
            like_rate = likes / views if views else 0
            comment_rate = comments / views if views else 0
            like_comment_ratio = likes / comments if comments else 0

            # Views per day
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

            # ---- Description Links ---- #
            description = snippet.get('description', '')
            links = extract_links(description)
            if links:
                with st.expander("🔗 Links in Video Description"):
                    for link in links:
                        st.markdown(f"- [{link}]({link})")

            # ---- Tags ---- #
            tags = snippet.get('tags', [])
            if tags:
                with st.expander(f"🏷️ Tags ({len(tags)} total)"):
                    st.write(", ".join(tags))

            # ---- Tabs ---- #
            tabs = st.tabs(["📊 Graphs", "📈 Advanced Stats", "🧠 Insights"])

            with tabs[0]:
                st.subheader("📊 Performance Comparison")
                df_bar = pd.DataFrame({
                    "Metric": ["Views", "Likes", "Comments"],
                    "Count": [views, likes, comments]
                })
                st.plotly_chart(px.bar(df_bar, x="Metric", y="Count",
                                       color="Metric", title="Performance Overview"),
                                use_container_width=True)

                st.subheader("📊 Engagement Breakdown")
                st.plotly_chart(px.pie(df_bar, names="Metric", values="Count",
                                       title="Distribution of Interactions"),
                                use_container_width=True)

                # Rates gauge charts
                st.subheader("⚡ Engagement Rates")
                col_g1, col_g2 = st.columns(2)

                with col_g1:
                    fig_gauge1 = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=like_rate * 100,
                        title={"text": "Like Rate (%)"},
                        gauge={
                            "axis": {"range": [0, 10]},
                            "bar": {"color": "#FF4B4B"},
                            "steps": [
                                {"range": [0, 2], "color": "#ffe0e0"},
                                {"range": [2, 5], "color": "#ffb3b3"},
                                {"range": [5, 10], "color": "#ff6666"},
                            ],
                            "threshold": {"line": {"color": "red", "width": 4}, "thickness": 0.75, "value": 4}
                        }
                    ))
                    st.plotly_chart(fig_gauge1, use_container_width=True)

                with col_g2:
                    fig_gauge2 = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=engagement * 100,
                        title={"text": "Engagement Rate (%)"},
                        gauge={
                            "axis": {"range": [0, 20]},
                            "bar": {"color": "#4B8BFF"},
                            "steps": [
                                {"range": [0, 5], "color": "#e0eaff"},
                                {"range": [5, 10], "color": "#b3c9ff"},
                                {"range": [10, 20], "color": "#668aff"},
                            ],
                            "threshold": {"line": {"color": "blue", "width": 4}, "thickness": 0.75, "value": 10}
                        }
                    ))
                    st.plotly_chart(fig_gauge2, use_container_width=True)

            with tabs[1]:
                st.subheader("📈 Derived Statistics")

                derived_data = {
                    "Metric": [
                        "Views",
                        "Likes",
                        "Comments",
                        "Like Rate (per 100 views)",
                        "Comment Rate (per 1000 views)",
                        "Like / Comment Ratio",
                        "Engagement Rate",
                        "Avg Views per Day",
                        "Video Duration",
                        "Days Since Published",
                    ],
                    "Value": [
                        f"{views:,}",
                        f"{likes:,}",
                        f"{comments:,}",
                        f"{like_rate * 100:.2f}%",
                        f"{comment_rate * 1000:.2f}",
                        f"{like_comment_ratio:.2f}",
                        f"{engagement:.4f}",
                        f"{int(views_per_day):,}" if views_per_day else "N/A",
                        format_duration(duration_sec) if duration_sec else "N/A",
                        f"{days_since}" if days_since else "N/A",
                    ]
                }
                st.dataframe(pd.DataFrame(derived_data), use_container_width=True)

                # Waterfall chart showing contribution
                st.subheader("📉 Interaction Funnel")
                fig_funnel = go.Figure(go.Funnel(
                    y=["Views", "Likes", "Comments"],
                    x=[views, likes, comments],
                    textinfo="value+percent initial",
                    marker={"color": ["#4B8BFF", "#FF4B4B", "#4BFF91"]}
                ))
                fig_funnel.update_layout(title="Viewer Interaction Funnel")
                st.plotly_chart(fig_funnel, use_container_width=True)

                # Tags bar chart if tags exist
                if tags:
                    st.subheader("🏷️ Tag Count Overview")
                    tag_df = pd.DataFrame({"Tag": tags[:20], "Length": [len(t) for t in tags[:20]]})
                    st.plotly_chart(
                        px.bar(tag_df, x="Tag", y="Length", title="Top 20 Tags by Character Length",
                               labels={"Length": "Tag Length (chars)"}),
                        use_container_width=True
                    )

            with tabs[2]:
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
                    st.success(f"💬 High discussion rate — very engaged community.")
                else:
                    st.info(f"💬 Balanced interaction between likes and comments.")

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
            st.error(str(e))
