# 智能客服系统文档网站

本文档网站为智能客服系统提供完整的技术文档和使用指南。

## 📚 文档内容

- **[首页](index.html)** - 系统概览和快速开始
- **[用户画像](user-profile.html)** - 三步走战略的用户画像系统
- **[API 文档](api-docs.html)** - WebSocket 聊天接口和智能推荐接口
- **[系统架构](architecture.html)** - 混合式用户画像提取架构设计
- **[智能记忆](memory-filter.html)** - 基于多因子综合评分的记忆检索算法

## 🚀 快速开始

### 本地预览

1. 克隆仓库到本地
2. 进入 `docs` 目录
3. 使用任意 HTTP 服务器预览，例如：

```bash
# 使用 Python
python -m http.server 8000

# 使用 Node.js
npx serve .

# 或直接在浏览器中打开 index.html
```

### GitHub Pages 部署

1. 将项目推送到 GitHub
2. 在仓库设置中启用 GitHub Pages
3. 选择 `docs` 文件夹作为源目录
4. 网站将自动部署到 `https://your-username.github.io/repository-name`

## 🎨 网站特性

- **响应式设计** - 支持桌面和移动设备
- **现代化 UI** - 美观的界面和流畅的交互
- **代码高亮** - 支持多种编程语言的语法高亮
- **搜索功能** - 快速查找文档内容
- **导航友好** - 清晰的导航结构和目录

## 📁 目录结构

```
docs/
├── index.html              # 主页
├── user-profile.html       # 用户画像文档
├── api-docs.html          # API 文档
├── architecture.html       # 系统架构文档
├── memory-filter.html      # 智能记忆文档
├── assets/
│   ├── css/
│   │   └── style.css      # 主样式文件
│   └── js/
│       └── main.js        # 主 JavaScript 文件
├── _config.yml            # Jekyll 配置
└── README.md              # 说明文档
```

## 🔧 自定义配置

### 修改网站信息

编辑 `_config.yml` 文件中的基本信息：

```yaml
title: "你的网站标题"
description: "你的网站描述"
url: "https://your-username.github.io"
baseurl: "/your-repository-name"
```

### 修改样式

编辑 `assets/css/style.css` 文件中的 CSS 变量：

```css
:root {
    --primary-color: #2563eb;    /* 主色调 */
    --secondary-color: #64748b;  /* 次要色调 */
    /* ... 其他颜色变量 */
}
```

### 添加新页面

1. 创建新的 HTML 文件
2. 使用相同的导航结构和样式
3. 更新所有页面的导航菜单

## 🌟 最佳实践

1. **保持一致性** - 使用统一的设计语言和导航结构
2. **优化性能** - 压缩图片和代码，使用 CDN
3. **SEO 友好** - 添加适当的 meta 标签和结构化数据
4. **移动优先** - 确保在所有设备上都有良好的用户体验
5. **定期更新** - 保持文档与代码同步

## 📝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/new-docs`)
3. 提交更改 (`git commit -am 'Add new documentation'`)
4. 推送到分支 (`git push origin feature/new-docs`)
5. 创建 Pull Request

## 📄 许可证

本文档网站采用 MIT 许可证。详见 [LICENSE](../LICENSE) 文件。

## 📞 联系我们

如有问题或建议，请通过以下方式联系我们：

- 📧 Email: team@example.com
- 🐛 Issue: [GitHub Issues](https://github.com/your-username/smart-customer-service-system/issues)
- 💬 讨论: [GitHub Discussions](https://github.com/your-username/smart-customer-service-system/discussions)

---

感谢使用智能客服系统！🎉
