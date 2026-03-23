module.exports = {
  apps: [
    {
      name: "safe-contract-front",
      script: "npm",
      args: "--prefix frontend run start",
      cwd: __dirname,
      watch: false,
      ignore_watch: [
        "node_modules",
        ".git",
        "frontend/.next",
        "frontend/node_modules",
        "logs",
      ],
      autorestart: true,
      max_memory_restart: "500M",
      env: {
        NODE_ENV: "production",
        PORT: "3000",
      },
      env_production: {
        NODE_ENV: "production",
        PORT: "3000",
      },
    },
    {
      name: "safe-contract-back",
      script: ".venv/bin/uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 8000",
      cwd: `${__dirname}/backend`,
      interpreter: "none",
      watch: false,
      autorestart: true,
      max_memory_restart: "500M",
      env: {
        PYTHONUNBUFFERED: "1",
        PATH: `${__dirname}/backend/.venv/bin:${process.env.PATH}`,
      },
      env_production: {
        PYTHONUNBUFFERED: "1",
        PATH: `${__dirname}/backend/.venv/bin:${process.env.PATH}`,
      },
    },
  ],
};
