# 🚀 YouTube Analytics Ultimate Dashboard

A Streamlit dashboard for analyzing YouTube channels and videos using the
**YouTube Data API v3** — channel health scoring, growth forecasting,
content-theme clustering, comment sentiment analysis, and more.

---

## ✨ Features

### Channel Analysis
- Channel overview: subscribers, total views, total videos, age, country, keywords, description links
- **Channel Health Score** — a composite 0–100 KPI (engagement + growth momentum + consistency) with a letter grade and gauge chart
- Top/bottom performing videos with thumbnails
- **Statistical anomaly detection** — flags viral outliers and underperforming videos via z-score
- Views, engagement, and correlation visualizations (histograms, scatter, box plot, heatmap)
- **Word cloud** of video titles
- **Upload schedule heatmap** (day of week × hour)
- **Shorts vs. long-form** split with performance comparison
- **Content theme clustering** (TF-IDF + KMeans) — auto-discovers recurring content themes from titles and ranks them by performance
- **90-day growth forecast** — linear trend extrapolation on cumulative views
- **Best-time-to-post** recommendation based on historical performance
- **Downloadable executive summary PDF** report
- CSV/Excel export on every data table

### Video Analysis
- Core stats: views, likes, comments, engagement, like rate, comment rate, views/day
- Accepts a video title *or* a direct YouTube URL
- Performance charts, engagement gauges, and an interaction funnel
- **Comment sentiment analysis** (VADER) — pie chart breakdown plus top positive/negative comments
- Derived-stats table and tag analysis, both exportable

### Compare Channels
- Compare up to 5 channels side-by-side: subscribers, total views, total videos, avg views/engagement (recent uploads)

### Compare Videos
- Compare up to 5 videos side-by-side: views, likes, comments, engagement rate

### General
- API response caching (30-minute TTL) to conserve YouTube API quota
- Custom styling (gradient header, styled metric cards, themed tabs)

---

## 🛠 Tech Stack

| Purpose | Library |
|---|---|
| UI / app framework | [Streamlit](https://streamlit.io) |
| Data handling | pandas, numpy |
| Charts | Plotly |
| YouTube data | google-api-python-client (YouTube Data API v3) |
| Word cloud | wordcloud, matplotlib |
| Sentiment analysis | vaderSentiment |
| Content clustering | scikit-learn (TF-IDF + KMeans) |
| PDF reports | reportlab |
| Excel export | xlsxwriter |
| Config | python-dotenv |

---

## 📦 Installation

1. **Clone or download this project**, then move into its folder.

2. **(Recommended) Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🔑 Getting a YouTube Data API Key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one).
3. Navigate to **APIs & Services → Library**, search for **YouTube Data API v3**, and enable it.
4. Go to **APIs & Services → Credentials → Create Credentials → API Key**.
5. Copy the generated key.

---

## ⚙️ Configuration

Create a `.env` file in the project root (same folder as `app.py`):

```
API_KEY=your_youtube_api_key_here
```

**Deploying to Streamlit Community Cloud?** Skip the `.env` file and instead add
this to your app's **Settings → Secrets**:

```toml
API_KEY = "your_youtube_api_key_here"
```

---

## ▶️ Running the App

```bash
streamlit run app.py
```

The app opens automatically in your browser, usually at `http://localhost:8501`.

---

## 🗂 Usage

1. Pick a **Mode** from the sidebar: `Channel Analysis`, `Video Analysis`, `Compare Channels`, or `Compare Videos`.
2. Enter a channel name, a video title/URL, or a list of names/URLs (one per line for comparison modes).
3. Click the corresponding **Analyze / Compare** button.
4. Explore the tabs — each mode organizes results into thumbnails, overview tables, graphs, insights, and (for channels) content clusters and a growth forecast.
5. Use the **CSV / Excel** buttons under any table to export data, or the **Download Executive Summary (PDF)** button in Channel Analysis → Insights for a shareable report.

---

## 📁 Project Structure

```
YouTube-Analytics-Dashboard/
│
├── app.py                     # Main Streamlit application
├── requirements.txt           # Python dependencies
├── README.md
├── .gitignore
├── LICENSE
├── .env                       # Your API key (not committed to version control)
│
└── screenshots/
    ├── home dashboard.png.png
    ├── channel analysis.png.png
    ├── Channel Overview.png.png
    ├── Video Analysis.png.png
    ├── Graph Analysis.png.png
    └── Graphs.png.png
```

---


## ⚠️ Notes & Limitations

- The YouTube Data API has a **default daily quota of 10,000 units**. Search calls
  are the most expensive; caching (30-min TTL) reduces repeat-lookup cost, but
  Compare Channels/Videos issues multiple API calls per run, so quota depletes
  faster there.
- Channel/video "growth forecast" is a simple linear trend over the fetched
  video sample — it's an explainable estimate, not a guaranteed prediction.
- Content clustering quality depends on how many videos are available and how
  distinct their titles are; very small channels may not produce meaningful clusters.
- Comment sentiment analysis only runs on videos with comments enabled and
  fetches up to the 100 most relevant comments (not the full comment history).

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) — free to use, modify, and distribute.

---

## 🤝 Contributing

Contributions are welcome!
Feel free to fork this repository, improve it, and submit a pull request.

---

## 👨‍💻 Author

**Biswarup Goswami**
🎓 B.Tech in Computer Science & Engineering
💻 Full Stack Developer | Python Developer | Data Analytics Enthusiast

- GitHub: [goswamibiswarup369-ops](https://github.com/goswamibiswarup369-ops)
- LinkedIn: [linkedin.com/in/biswarup-goswami-27881b2b9](https://www.linkedin.com/in/biswarup-goswami-27881b2b9)

---

## ⭐ Support

If you found this project useful, please consider giving it a ⭐ Star on GitHub.
Your support motivates me to build more useful open-source projects.
