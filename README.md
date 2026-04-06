# FinsightAI

An AI-powered financial insights application built with React, TypeScript, and Tailwind CSS.

## Live Demo

The frontend is deployed to GitHub Pages: **[https://utsnlpgroup.github.io/FinInsightAI/](https://utsnlpgroup.github.io/FinInsightAI/)**

## Project Structure

```
finsightAI/
└── frontend/          # React + TypeScript + Vite frontend
    ├── src/           # Source code
    ├── public/        # Static assets
    ├── index.html
    └── package.json
```

## Frontend

Built with:
- [React 19](https://react.dev/)
- [TypeScript](https://www.typescriptlang.org/)
- [Vite](https://vitejs.dev/)
- [Tailwind CSS v4](https://tailwindcss.com/)

### Local Development

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

### Build

```bash
cd frontend
npm run build
```

The production build outputs to `frontend/dist/`.

## Deployment

The frontend is automatically deployed to **GitHub Pages** on every push or pull request merge to `main` via the [deploy workflow](.github/workflows/deploy.yml).

## License

MIT
