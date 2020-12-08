
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
  
  get_video();
  get_list();
  get_queue();

  // this actually does get called
  if($('#username').val()===''){
    username ='';
    u1s = ['red','green','purple','orange','salmon','pink','brick','violet','blue','grey','fuchsia','gold'
          ,'indigo','ivory','cyan']
    u2s = ['womble','cat','bear','tree','wombat','skunk','elephant','badger','warrior','dog','rabbit','fish'
          ,'wolf','ant','antelope','ape','baboon','bee','bobcat','buffalo','cobra','coyote','ferret','emu']

    username = u1s[getRandomInt(0,u1s.length - 1)] + ' ' + u2s[getRandomInt(0,u1s.length-1)];
    // console.log('generated ' + username);
    $.growl.notice({ message: "Assigning random username!" });
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

function isEmptyOrSpaces(str){
  return str === null || str.match(/^\s*$/) !== null;
}

// todo: should be just stuffed in an object or something
var playing = 0;
var playTimer = null;
var hardUpdateTime = 5000; // 5 seconds
var softUpdateTime = 500; // .5 seconds
var lastCalled = (new Date).getTime();

var videos = {};
var queue = {};

var length = 0;
var played = 0;

/** manage times since progress checked and updated */
function update_time(){
  var crntTime = (new Date).getTime();

  // don't do a full update too often, just update the progress bar
  if(crntTime> (lastCalled + hardUpdateTime)){
    // get_video();
    lastCalled = crntTime;
  }else{
    played += softUpdateTime / 1000;
  }

  set_progress();
  
  playTimer = setTimeout(update_time, softUpdateTime);
}

function set_progress(){
  $('#video_progress').css('width','' + played/length * 100 + '%');
}

/** set up timer to refresh video status */
function set_play_state(p){
  playing = p;
  if(playing && !playTimer){
    $.growl.notice({ message: "Starting playstate update timer" });
    playTimer = setTimeout(update_time, softUpdateTime); // 1000 = 1 sec
  }else if(!playing && playTimer){
    // need to clear video length thing

    // clearTimeout(playTimer);
    // $.growl.notice({ message: "Stopping playstate update timer" });
  }
}


// player controls
function stop(){
  $.getJSON($SCRIPT_ROOT + '/_stop', {
    }, function(data) {
        if(data.result.length===0){
          console.log('no data')
        }else{
          console.log(data.result);
        }
    });
}
function next(){
  $.getJSON($SCRIPT_ROOT + '/_next', {
    }, function(data) {
        if(data.result.length===0){
          console.log('no data')
        }else{
          console.log(data.result);
        }
    });
}
function prev(){
  $.getJSON($SCRIPT_ROOT + '/_prev', {
    }, function(data) {
        if(data.result.length===0){
          console.log('no data')
        }else{
          console.log(data.result);
        }
    });
}
function play(){
  $.getJSON($SCRIPT_ROOT + '/_play', {
    }, function(data) {
        if(data.result.length===0){
          console.log('no data')
        }else{
          console.log(data.result);
        }
    });
}

function play_pause(){
  $.getJSON($SCRIPT_ROOT + '/_play_pause', {
    }, function(data) {
        if(data.result.length===0){
          console.log('no data')
        }else{
          console.log(data.result);
        }
    });
}




/**
 * get current playing video & play time
 */
function get_video(){
    $.getJSON($SCRIPT_ROOT + '/_get_video', {
      }, function(data) {
        if(data === null || data.result === null){
          $('#currentlyPlaying').val('Nothing playing');
          update_time();
        }else{
          $('#currentlyPlaying').val(data.result.filename);

          length = data.result.length;
          played = data.result.played
          $('#video_progress').prop('aria-valuemax', data.result.length);
          $('#video_progress').prop('aria-valuenow', data.result.played);
          
          set_progress();

          // set_play_state(data.result.playing);

        }
      });
}

/**
 * remove duplicates
 */
function clean_video_list(){
  $.getJSON($SCRIPT_ROOT + '/_clean_video_list', {

    }, function(data) {
        if(data.result.length===0){
          console.log('no data');
          $.growl.error({ message: 'Nothing back'});
        }else{
          $.growl.notice({ message: 'We did it bro, we totally pulled it off' });
          get_list();
          console.log(data.result);
        }
    });
}

function delete_video(id){
  $.getJSON($SCRIPT_ROOT + '/_delete_video', {
      videoId: id,
      addedBy: $('#username').val(),
    }, function(data) {
        if(data.result.length===0){
          console.log('no data');
          $.growl.error({ message: 'Couldn\'t delete'});
        }else{
          $.growl.notice({ message: 'Deleting ' + data.result.title });
          // probably could return this from _delete_video, dunno if that make sense
          get_list();
          console.log(data.result);
        }
    });
}

function get_play_targets(){
  $.getJSON($SCRIPT_ROOT + '/_get_play_targets', {}, function(data) {
        if(data.result.length===0){
          console.log('no data');
          $.growl.error({ message: 'no play targets'});
        }else{
          $.growl.notice({ message: 'found play targets' });
          $('#play_targets').empty()
          $.each(data.result, function(i, val){
            $('#play_targets').append(new Option(val.name, val.uuid));
          });
          console.log(data.result);
        }
    });
}

function play_video(id){
    $.getJSON($SCRIPT_ROOT + '/_play_video', {
        videoId: id,
        addedBy: $('#username').val(),
      }, function(data) {
          if(data.result.length===0){
            console.log('no data');
            $.growl.error({ message: 'Couldn\'t add'});
          }else{
            $.growl.notice({ message: 'Adding ' + data.result.title });
            // probably could return queue array from play_video to skip extra call
            get_queue();
            console.log(data.result);
          }
      });
}

function get_file_info(videoId){
  
  $.getJSON($SCRIPT_ROOT + '/_get_file_info', {
        videoId: videoId
    }, function(data) {
      
      if(data.result.length===0){
        $.growl.error({ message: 'something shat itself' });
      }else{
        // $.growl.notice({ message: 'file info ' + data.result });
        $('.video_info_'+videoId).html(data.result.codec_name);
        console.log(data.result);
      }
    });
}

function convert_video(videoId){
  $.getJSON($SCRIPT_ROOT + '/_convert_video', {
    videoId: videoId
}, function(data) {
  
  if(data.result.length===0){
    $.growl.error({ message: 'something shat itself' });
  }else{
    // $.growl.notice({ message: 'file info ' + data.result });
    console.log(data.result);
  }
});
}

function download_video(){
  $.growl.notice({ message: 'Downloading ' + $('#youtubeUrl').val() });
  $.getJSON($SCRIPT_ROOT + '/_download_video', {
        url: $('#youtubeUrl').val(),
        addedBy: $('#username').val(),
    }, function(data) {
      
      if(data.result.length===0){
        $.growl.notice({ message: 'Some kind of error downloading ' + $('#youtubeUrl').val() });
      }else{
        $.growl.notice({ message: 'Succeeded downloading ' + data.result.title });
        console.log(data.result);
      }
    });
}

function clear_queue(){
  $.getJSON($SCRIPT_ROOT + '/_clear_queue', {
  }, function(data) {
      if(data.result) {
        $.growl.notice({ message: "Cleared Queue" });
        $('#queue').html('');
      } else {
        $.growl.error({ message: "Something broke clearing queue" });
      }
  });
}

/** get the current queue */
function process_queue(){
  $.getJSON($SCRIPT_ROOT + '/_process_queue', {
  }, function(data) {
      if(data.result.length===0) {
        console.log('nothing queued')
        
      } else {
        
      }
  });
}

function set_queue_position(order){
  $.getJSON($SCRIPT_ROOT + '/_set_queue_position', {
    order: order
  }, function(data) {

      if(data.result.length===0) {
        console.log('blarp')
      } else {
        
      }
  });
}

/** get the current queue */
function get_queue(){
    $.getJSON($SCRIPT_ROOT + '/_get_queue', {
    }, function(data) {
        var fileList = '';

        if(data.result.length===0) {
          console.log('nothing queued')
          $('#files').html('no queue');
        } else {

          $.each(data.result, function(i, val) {
              fileList += '<a onclick="set_queue_position(\''+val.order+'\')">'+val.order+' - '+val.title+'</a><br>';
          });
          $('#queue').html(fileList);
        }
    });
}

function scan_folder(){
  $.getJSON($SCRIPT_ROOT + '/_scan_folder', {
  }, function(data) {

      if(data.result.length===0) {
        console.log('nothing nothing')
      } else {

      }
  });
}

function searchUL(searchBoxId, ulId) {
  var input, filter, ul, li, a, i, txtValue;
  // search box
  input = document.getElementById(searchBoxId);
  filter = input.value.toUpperCase();
  ul = document.getElementById(ulId);
  li = ul.getElementsByTagName("li");
  // not sure how well this will work with 1000 items
  for (i = 0; i < li.length; i++) {
      a = li[i].getElementsByTagName("a")[0];
      txtValue = a.textContent || a.innerText;
      if (txtValue.toUpperCase().indexOf(filter) > -1) {
          li[i].style.display = "";
      } else {
          li[i].style.display = "none";
      }
  }
}

/**
 * set rating for a song then refresh list
 */
function rate(videoId, rating){
  $.getJSON($SCRIPT_ROOT + '/_rate', {
      'videoId': videoId,
      'rating': rating
  }, function(data) {
      if(data.result.length===0) {
        console.log('no files')
        $('#files').html('no files');
      } else {
        videos = data.result;
        draw_video_list();
        // todo: this doesn't work
        searchUL('videoSearch', 'videoUL');
      }
  });
}

/**
 * get the video list and populate the controls that manage it,
 * currently just #videoUL
 */
function get_list(){
    $.getJSON($SCRIPT_ROOT + '/_list_videos', {
        // test: 'test',
    }, function(data) {
        if(data.result.length===0) {
          console.log('no files')
          $('#files').html('no files');
        } else {
          videos = data.result;
          draw_video_list();
        }
    });
}

function draw_video_list(){
  var videoULLi = '';
  $.each(videos, function(i, val) {
    videoULLi += '<li class="align-items-center"><a>' + 
      val.title + ' <i>' + val.addedBy + '</i><br>' + val.filename + ' <span class="badge badge-primary badge-pill">' + val.rating + '</span><br>'+
      'Codec: <span class="video_info_' + val.videoId + '"></span>' + 
      '</a>' +
      '<button class="btn" onclick="play_video(\''+val.videoId+'\')">play now</button>'+
      '<button class="btn" onclick="play_video(\''+val.videoId+'\')">queue</button>'+
      '<button class="btn" onclick="if(confirm(\'delete '+val.title+'?\')){ delete_video(\''+val.videoId+'\'); }">delete</button>' +
      '<button class="btn" onclick="get_file_info(\''+val.videoId+'\')">get file info</button>' +
      '<button class="btn" onclick="if(confirm(\'convert '+val.title+' to h264 1080p?\')){ convert_video(\''+val.videoId+'\'); }">convert video</button>' +
      '<button onclick="rate('+val.videoId+',1)">1</button><button onclick="rate('+val.videoId+',2)">2</button><button onclick="rate('+val.videoId+',3)">3</button><button onclick="rate('+val.videoId+',4)">4</button><button onclick="rate('+val.videoId+',5)">5</button>'+
      '</li>'
  });
  $('#videoUL').html(videoULLi);
}