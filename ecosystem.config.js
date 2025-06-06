module.exports = {
  apps : [
    {
      name: "backend",
      script: "uv",
      args: "run server.py",
      cwd: "/home/pi/replifactory_v7/backend",
      autorestart: true,
      watch: false
    },
    {
      name: "frontend",
      script: "/home/pi/replifactory_v7/vue/src/server/express_server.js",
      cwd: "/home/pi/replifactory_v7/vue",
      autorestart: true,
      watch: false
    }
  ]
};
