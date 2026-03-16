module.exports = {
  apps: [
    {
      name: "safe-contract-front",
      script: "npm",
      args: "--prefix frontend run start",
      cwd: __dirname,
      watch: true,
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
  ],
};
