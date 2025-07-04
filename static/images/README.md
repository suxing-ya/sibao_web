# 静态图片文件目录

## 使用说明

1. 将你的背景图片文件重命名为 `back.jpeg`
2. 将图片文件放置在此目录下 (`static/images/back.jpeg`)
3. 支持的图片格式：`.jpeg`, `.jpg`, `.png`, `.gif`, `.webp`

## 图片要求

- **背景图片 (back.jpeg)**
  - 推荐尺寸：1920x1080 或更高
  - 文件大小：建议小于2MB
  - 格式：JPEG格式（较小文件大小）

## 如果要使用其他图片名称

如果你想使用其他名称的图片，请修改 `templates/index.html` 文件中的路径：

```html
background-image: url("{{ url_for('static', filename='images/你的图片名称.jpg') }}");
```

## 目录结构

```
static/
├── images/
│   ├── back.jpeg          # 首页背景图
│   ├── logo.png           # 网站logo（如需要）
│   └── other-images...    # 其他图片文件
├── css/                   # CSS文件（如需要）
├── js/                    # JavaScript文件（如需要）
└── README.md             # 说明文件
``` 