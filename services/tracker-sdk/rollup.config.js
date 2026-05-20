import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import typescript from '@rollup/plugin-typescript';
import terser from '@rollup/plugin-terser';

const production = !process.env.ROLLUP_WATCH;

export default {
  input: 'src/index.ts',
  output: [
    {
      file: 'dist/tracker.js',
      format: 'umd',
      name: 'AdTracker',
      sourcemap: true,
    },
    {
      file: 'dist/tracker.esm.js',
      format: 'es',
      sourcemap: true,
    },
    {
      file: 'dist/tracker.min.js',
      format: 'umd',
      name: 'AdTracker',
      sourcemap: true,
      plugins: [terser()],
    },
  ],
  plugins: [
    resolve(),
    commonjs(),
    typescript({
      tsconfig: './tsconfig.json',
      declaration: true,
      declarationDir: './dist',
    }),
  ],
};
