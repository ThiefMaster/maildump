var gulp = require('gulp');
var merge2 = require('merge2');
var autoprefixer = require('gulp-autoprefixer');
var minifyCss = require('gulp-minify-css');
var sass = require('gulp-sass');
var uglify = require('gulp-uglify');
var concat = require('gulp-concat');

var paths = {
  'javascript': [
    'js/lib/jquery.js',
    'js/lib/jquery-ui.js',
    'js/lib/jquery.hotkeys.js',
    'js/lib/handlebars.js',
    'js/lib/moment.js',
    'js/lib/socket.io.js',
    'js/lib/jstorage.js',
    'js/util.js',
    'js/message.js',
    'js/maildump.js'
  ],
  'css': ['css/**/*.css'],
  'scss': ['css/**/*.scss']
}

gulp.task('app-css', function() {
  return merge2(
    gulp.src(paths['scss'])
    .pipe(sass().on('error', sass.logError)),
    gulp.src(paths['scss'])
    .pipe(autoprefixer()),
    gulp.src(paths['css'])
    .pipe(autoprefixer())
  )
  .pipe(minifyCss())
  .pipe(concat('style.css'))
  .pipe(gulp.dest('build/css'));
});

gulp.task('app-js', function() {
  return merge2(
    gulp.src(paths['javascript'])
    .pipe(uglify())
  )
  .pipe(concat('maildump.js'))
  .pipe(gulp.dest('build/js'));
});

gulp.task('build', ['app-css', 'app-js'], function() {
});