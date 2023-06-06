module.exports = {
  configureWebpack: {
    resolve: {
      fallback: {
        "stream": require.resolve("stream-browserify"),
        "assert": require.resolve("assert/")
      },
    },
    },
  productionSourceMap: true,
  chainWebpack: (config) => {
    config.resolve.alias.set('vue', '@vue/compat')
    config.module
      .rule('vue')
      .use('vue-loader')
      .tap((options) => {
        return {
          ...options,
          compilerOptions: {
            compatConfig: {
              MODE: 2
            }
          }
        }
      })
  }
}
