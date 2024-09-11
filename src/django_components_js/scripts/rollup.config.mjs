import packageJson from '../package.json' assert { type: 'json' };

import { babel } from '@rollup/plugin-babel';
import terser from '@rollup/plugin-terser';
import { nodeResolve } from '@rollup/plugin-node-resolve';
import typescript from '@rollup/plugin-typescript';

const extensions = ['.ts', '.tsx', '.js', '.jsx', '.es6', '.es', '.mjs'];
const banner = `/*!
* ${packageJson.name} v${packageJson.version}
* Released under the MIT License.
*/\n`;

export default [
  {
    input: 'src/index.ts',
    output: [
      // Build a distro that can be installed by inserting a <script> tag
      {
        file: 'dist/cdn.js',
        name: 'Components',
        format: 'umd',
        globals: {
          // NOTE: Use this to define dependencies, e.g.:
          // 'alpine-reactivity': 'AlpineReactivity',
        },
        sourcemap: true,
        banner,
      },
      // Build a distro that can be installed by inserting a <script> tag (minified)
      {
        file: 'dist/cdn.min.js',
        name: 'Components',
        format: 'umd',
        globals: {
          // NOTE: Use this to define dependencies, e.g.:
          // 'alpine-reactivity': 'AlpineReactivity',
        },
        plugins: [
          terser({
            format: { comments: /^!/, ecma: 2015, semicolons: false },
          }),
        ],
        sourcemap: true,
        banner,
      },
    ],
    // NOTE: Use this to define dependencies
    // external: ['alpinejs', 'alpine-reactivity'],
    plugins: [
      nodeResolve({ extensions }),
      typescript(),
      babel({
        extensions,
        babelHelpers: 'inline',
      }),
    ],
  },
];
