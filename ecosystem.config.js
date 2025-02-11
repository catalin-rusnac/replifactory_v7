module.exports = {
  apps : [
    {
      name: "backend",
      script: "uv",
      args: "run server.py",
      cwd: "~/replifactory_v7/flask_app",
      autorestart: true,
      watch: false
    },
    {
      name: "frontend",
      script: "~/replifactory_v7/vue/src/server/express_server.js",
      cwd: "~/replifactory_v7/vue",
      autorestart: true,
      watch: false
    }
  ]
};
