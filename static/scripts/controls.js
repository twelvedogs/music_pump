
/**
 * Returns a random integer between min (inclusive) and max (inclusive).
 * The value is no lower than min (or the next integer greater than min
 * if min isn't an integer) and no greater than max (or the next integer
 * lower than max if max isn't an integer).
 * Using Math.round() will give you a non-uniform distribution!
 */
function getRandomInt(min, max) {
  min = Math.ceil(min);
  max = Math.floor(max);
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

// var myPlayer = null;
$(function() {
  
  get_song();
  get_list();

  // this actually does get called
  if($('#username').val()===''){
    username ='';
    u1s = ['red','green','purple','orange','yellow','pink','white','black','blue','grey']
    u2s = ['womble','cat','bear','tree','wombat','skunk','elephant','badger','warrior','dog','rabbit','fish','wolf']

    username = u1s[getRandomInt(0,u1s.length)] + ' ' + u2s[getRandomInt(0,u1s.length)];
    console.log('generated ' + username);
    $('#username').val(username);
  }
    //alert('page loaded');
    // videojs("example_video_1").ready(function(){
    //     myPlayer = this;

    //     // EXAMPLE: Start playing the video.
    //     console.log('playing')
    //     // myPlayer.play();

    // });

    // $('input[type=text]').bind('keydown', function(e) {
    //   if (e.keyCode == 13) {
    //     submit_form(e);
    //   }
    // });

    // $('input[name=a]').focus();
});

function raw_command(cmd, callback){
    $.getJSON($SCRIPT_ROOT + '/_raw_command', {
        cmd: cmd,
    }, function(data) {
        if(data.result.length===0){
          console.log('no data')
        }else{
          callback(data.result);
          console.log(data.result);
        }
    });
}

function play_pause(){
    $.getJSON($SCRIPT_ROOT + '/_play_pause', {
          // url: $('#youtubeUrl').val(),
      }, function(data) {
          if(data.result.length===0){
            console.log('no data')
          }else{
            console.log(data.result);
          }
      });
}

function isEmptyOrSpaces(str){
  return str === null || str.match(/^\s*$/) !== null;
}

function get_song(){
    $.getJSON($SCRIPT_ROOT + '/_get_song', {
      }, function(data) {
        console.log('response', data)
        if(data === null || isEmptyOrSpaces(data.result)){
          console.log('no data')
          $('#currentlyPlaying').val('Nothing playing');
        }else{
          console.log(data.result);
          $('#currentlyPlaying').val(data.result);
        }
      });
}

function get_length(){
    $.getJSON($SCRIPT_ROOT + '/_get_length', {
      }, function(data) {
          if(data.result.length===0){
            console.log('no data')
          }else{
            $('#song_length').val(data.result);
            console.log(data.result);
          }
      });
}
// function get_remaining(){
//   $.getJSON($SCRIPT_ROOT + '/_get_remaining', {
//     }, function(data) {
//         if(data.result.length===0){
//           console.log('no data')
//         }else{
//           $('#song_length').val(data.result);
//           console.log(data.result);
//         }
//     });
// }

function play_video(id){
    console.log('attempting to play: ' + id)
  
    $.getJSON($SCRIPT_ROOT + '/_play_video', {
        videoId: id,
      }, function(data) {
          if(data.result.length===0){
            console.log('no data')
          }else{
            console.log(data.result);
          }
      });
}

function download_video(){
  console.log('attempting to dl: ' + $('#youtubeUrl').val())
  
  $.getJSON($SCRIPT_ROOT + '/_download_video', {
        url: $('#youtubeUrl').val(),
        addedBy: $('#username').val(),
    }, function(data) {
        if(data.result.length===0){
          console.log('no data')
        }else{
          console.log(data.result);
        }
    });
}

/** get the current queue */
function get_queue(){
    $.getJSON($SCRIPT_ROOT + '/_get_queue', {
        // test: 'test',
    }, function(data) {
        var fileList = '';

        if(data.result.length===0) {
          console.log('nothing queued')
          $('#files').html('no queue');
        } else {

          $.each(data.result, function(i, val) {
              fileList += '<a onclick="play_video(\''+val.videoId+'\')">'+val.title+'</a><br>';
          });
          $('#queue').html(fileList);
        }
    });
}

/**
 * get the video list and populate the controls that manage it,
 * currently just #videoUL
 */
function get_list(){
    $.getJSON($SCRIPT_ROOT + '/_list_videos', {
        test: 'test',
    }, function(data) {
        var fileList = '';
        var videoULLi = '';
        if(data.result.length===0) {
          console.log('no files')
          $('#files').html('no files');
        } else {
          // create the option html and just stuff it in the control
          // #files is going away
          $.each(data.result, function(i, val) {
            videoULLi += '<li><a href="#" onclick="play_video(\''+val.videoId+'\')">' + val.title + ' - click to enque again play for now</a></li>'
            //fileList += '<a onclick="play_video(\''+val.videoId+'\')">'+val.title+'</a><br>';
          });
          $('#videoUL').html(videoULLi);
          //$('#files').html(fileList);
        }
    });
}

function rate_video(){
    $.getJSON($SCRIPT_ROOT + '/_rate_video', {
        rating: '5',
    }, function(data) {
        if(data.result.length===0){
          console.log('no response')
        }else{
          alert('done')
        }
    });
}