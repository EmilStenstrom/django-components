const fsp = require('fs/promises');
const path = require('path');

// This function runs AFTER we build the JS code
const main = async () => {
  // Make the built script available in Django as static file
  // See https://testdriven.io/blog/django-static-files/
  const DEST_DIR = '../django_components/static/django_components';

  await fsp.mkdir(DEST_DIR, { recursive: true });
  await fsp.copyFile('./dist/cdn.min.js', path.join(DEST_DIR, 'django_components.min.js'));
};

main();
