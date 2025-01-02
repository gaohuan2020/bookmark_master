# Bookmark Organization Master

A bookmark tag organization tool based on browser extension and Python backend

## Features

- Quick webpage content extraction
- One-click operation via browser extension
- Automated content processing and saving
- Advanced search capabilities:
  - Full-text search in browsing history
  - Smart bookmark search with tags
  - Search filters by date and domain
  - Search history tracking

## Requirements

- Python 3.10+
- Edge Browser (version 90+)
- Supported OS: Windows/MacOS/Linux

## Installation

### 1. Install Python Dependencies

bash
pip install -r requirements.txt

### 2. Install Browser Extension
1. Open Edge browser
2. Go to extensions page (edge://extensions/)
3. Enable "Developer mode"
4. Click "Load unpacked extension"
5. Select the `extension` folder in the project

## Service Setup
1. Configure Deepseek api_key in app.py
![alt text](image.png)

2. Start backend service:
```bash
python app.py
```

2. Service runs on `http://localhost:5000` by default

## Usage

1. Open any webpage in browser
2. Click the extension icon
3. Click "bookmark Analysis" button to obtain bookmark analysis results
4. Click "bookmark Organize" button to organize bookmarks

## Todo List

- [ ] Fix Zhihu page access issues
  - [ ] Handle Zhihu anti-crawler mechanism
  - [ ] Optimize Zhihu page content extraction
  - [ ] Add user agent simulation
- [ ] Optimize error handling
- [ ] Add support for more models
- [ ] Enhance search capabilities
  - [ ] Implement full-text search for history and bookmarks

## Common Issues

1. If extension fails to connect to backend, check:
   - If backend service is running properly
   - If port is occupied
   - Firewall settings

2. If content extraction fails:
   - Verify if webpage is accessible
   - For Zhihu pages, fix is in progress

3. If unable to delete existing tags:
   - Verify browser sync is turned off

## License

MIT License

## Contact

For issues, please submit an Issue or Pull Request.