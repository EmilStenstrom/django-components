module.exports = {
  preset: 'ts-jest',
  transform: {
    '^.+\\.(ts|tsx)?$': 'ts-jest',
    '^.+\\.(js|jsx)$': 'babel-jest',
  },
  verbose: false,
  testEnvironment: 'jsdom',
  testEnvironmentOptions: {
    customExportConditions: ['node', 'node-addons'],
  },
  roots: [
    '<rootDir>/src',
  ],
  setupFilesAfterEnv: [
    '<rootDir>/test/setup.js',
  ],
  moduleFileExtensions: [
    'tsx',
    'ts',
    'js',
  ],
  moduleDirectories: [
    'node_modules',
  ],
  collectCoverageFrom: [
    'src/**/*.{js,ts,tsx}',
    '!**/*.d.ts',
  ],
  snapshotSerializers: [
    'jest-serializer-html',
  ],
  testMatch: [
    '**/__tests__/**/*.spec.{js,ts,tsx}',
  ],
}
