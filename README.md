# 🚀 YouTube Analytics Dashboard

An advanced YouTube Analytics Dashboard built using **Python**, **Streamlit**, **Plotly**, and the **YouTube Data API v3**. This project enables users to analyze YouTube channels and individual videos through interactive visualizations, performance metrics, and actionable insights.

---

## 🌟 Overview

This dashboard provides comprehensive analytics for YouTube creators, marketers, and data enthusiasts. Users can explore channel growth, video engagement, audience interactions, and performance trends through a clean and interactive interface.

---

## ✨ Features

### 📺 Channel Analysis
- Search any public YouTube channel
- View subscriber count, total views, and uploaded videos
- Display channel description and keywords
- Extract links from channel description
- Top 5 & Bottom 5 performing videos
- Average views and engagement rate
- Viral video detection
- Channel performance consistency analysis

### 🎥 Video Analysis
- Search any YouTube video
- View video statistics
- Engagement Rate
- Like Rate
- Comment Rate
- Like-to-Comment Ratio
- Average Views Per Day
- Video Duration
- Upload Date
- Video Tags
- Description Links
- HD/SD Quality Detection

---

## 📊 Interactive Visualizations

- 📈 Views Trend
- 📊 Views Distribution
- ❤️ Engagement Distribution
- 📉 Views vs Likes Analysis
- 📦 Box Plot for Outlier Detection
- 🔥 Correlation Heatmap
- 🎯 Funnel Chart
- 🥧 Pie Charts
- 📊 Bar Charts
- ⚡ Gauge Charts

---

## 🧠 Smart Insights

The dashboard automatically generates:

- 🏆 Best Performing Video
- 📉 Worst Performing Video
- 📈 Channel Growth Analysis
- 🔥 Viral Video Detection
- 📊 Performance Consistency
- 💬 Engagement Analysis
- 🎯 Optimization Suggestions

---

## 🛠️ Tech Stack

- Python
- Streamlit
- Plotly
- Pandas
- NumPy
- Google YouTube Data API v3
- Google API Python Client
- Statsmodels

---

## 📂 Project Structure

```text
YouTube-Analytics-Dashboard/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── LICENSE
│
├── assets/
│   └── demo.mp4
│
└── screenshots/
    ├── home-dashboard.png
    ├── channel-analysis.png
    ├── video-analysis.png
    ├── graphs.png
    └── insights.png
```

---

## 🚀 Installation

### Clone the repository

```bash
git clone https://github.com/your-username/youtube-analytics-dashboard.git
```

### Navigate to the project folder

```bash
cd youtube-analytics-dashboard
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the application

```bash
streamlit run app.py
```

---

## 🔑 API Configuration

Create your own **YouTube Data API v3** key from Google Cloud Console.

Create a `.env` file:

```env
YOUTUBE_API_KEY=YOUR_API_KEY
```

Load it in Python:

```python
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
```

> **Note:** Never expose your API key in a public repository.

---


## 🚀 Future Enhancements

- 🤖 AI-powered Recommendations
- 📈 Subscriber Growth Prediction
- 📊 Channel Comparison
- 📄 Export Reports (PDF & Excel)
- 🌙 Dark Mode
- 🌐 Multi-language Support

---

## 🤝 Contributing

Contributions are welcome!

Feel free to fork this repository, improve it, and submit a pull request.

---

## 👨‍💻 Author

**Biswarup Goswami**

🎓 B.Tech in Computer Science & Engineering

💻 Full stack Developer | Python Developer | Data Analytics Enthusiast

- GitHub: https://github.com/your-github-username
- LinkedIn: www.linkedin.com/in/biswarup-goswami-27881b2b9

---

## ⭐ Support

If you found this project useful, please consider giving it a **⭐ Star** on GitHub.

Your support motivates me to build more useful open-source projects.

---

## 📄 License

This project is licensed under the **MIT License**.
