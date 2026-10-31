// Firebase web config for the TEST environment.
// Copy the values from Firebase console → Project settings → General → Your apps → Web app → SDK setup (Config).
// These values are not secret: access is controlled by Google sign-in + firestore.rules (allowlist).
window.MUDRA_ENV = {
  name: 'test',
  firebase: {
    apiKey: 'REPLACE_ME',
    authDomain: 'REPLACE_ME.firebaseapp.com',
    projectId: 'REPLACE_ME',
    storageBucket: 'REPLACE_ME.firebasestorage.app',
    messagingSenderId: 'REPLACE_ME',
    appId: 'REPLACE_ME'
  }
};
