
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

function save_username(){
  Cookies.set('username', $('#username').val(), { expires: 365, SameSite: 'Lax' });
}

// var myPlayer = null;
$(function() {
  
  get_video();
  get_list();
  get_queue();

  if(Cookies.get('username')!==''){
    $('#username').val(Cookies.get('username'));
  }

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

function update_queue(queue){
  file_list = '';
  $.each(queue, function(i, val) {
    file_list += '<a onclick="set_queue_position(\''+val.order+'\')">'+val.order+' - '+val.title+'</a><br>';
  });
  $('#queue').html(file_list);
}

// don't really know what to call this, Storage_Object_With_Listeners is pretty clunky
class Data{
  constructor() {

    this.length = 0;
    this.time_start = null;
    this.played = 0; // song progress on server

    // these are definitely used
    this.videos = {};
    this.queue = {};
    this.playing_video = {};

    this.listeners = [];

  }

  /** add listener to a property, if it's set with set() the listener function is called */
  add_listener(prop, fn){
    this.listeners.push({property: prop, listener: fn});
  }

  call_listeners(prop){
    // i really don't know how 'this' works in js
    let parent_this = this;
    $.each(this.listeners, function(i, listener){
      if(listener.property === prop){
        listener.listener(parent_this[prop]);
      }
    });
  }

  // how do people handle changing a single property on the property?
  set(prop, val){
    this[prop]=val;
    // call after set so listeners get new value
    this.call_listeners(prop);
  }
}

var data = new Data();
data.add_listener('queue', update_queue);
data.add_listener('videos', draw_video_list);
data.add_listener('playing_video', start_playing); // this might be called after video has started?

function start_playing(){
  data.set('time_start', get_seconds_since_epoch());
  console.log(data.video);
  $('#currentlyPlaying').val(data.playing_video.title);
  set_progress(0, data.playing_video.length+120); // hack to get some kind of action
}

function get_seconds_since_epoch(){
  return Math.round((new Date()).getTime() / 1000);
}

function update_playing(){
  //data.set('time_start', new Date());
  // played = get_seconds_since_epoch()-start
  seconds_since_epoch-data.time_start;
  console.log(data.playing_video);
  set_progress(seconds_since_epoch - data.time_start, data.playing_video.length);
}

// TODO: cull unused, probably most of them since most functionality is broken rn

// repeat with the interval of 2 seconds
let progress_update_timer = setInterval(() => update_playing, 1000);

// after 5 seconds stop
// setTimeout(() => { clearInterval(timerId); alert('stop'); }, 5000);

function set_progress(played, length){
  console.log('setting to', played, length);
  $('#video_progress').css('width','' + played/length * 100 + '%');
}


// player controls
function stop(){
  $.getJSON($SCRIPT_ROOT + '/_stop', {
    }, function(response) {
        if(response.result.length===0){
          console.log('stop no response')
        }else{
          console.log(response.result);
        }
    });
}
function next(){
  $.getJSON($SCRIPT_ROOT + '/_next', {
    }, function(response) {
      if(response.length===0){
        console.log('no response')
      }else{
        data.set('playing_video', response.video);
        data.set('queue', response.queue);
      }
    });
}
function prev(){
  $.getJSON($SCRIPT_ROOT + '/_prev', {
    }, function(response) {
        if(response.length===0){
          console.log('no response')
        }else{
          data.set('playing_video', response.video);
          data.set('queue', response.queue);
          // TODO: set queue position
        }
    });
}
function play(){
  $.getJSON($SCRIPT_ROOT + '/_play', {
    }, function(response) {
        if(response.result.length===0){
          console.log('no response')
        }else{
          console.log(response.result);
        }
    });
}

function play_pause(){
  $.getJSON($SCRIPT_ROOT + '/_play_pause', {
    }, function(response) {
        if(response.result.length===0){
          console.log('no response')
        }else{
          console.log(response.result);
        }
    });
}




/**
 * get current playing video & play time
 */
function get_video(){
    $.getJSON($SCRIPT_ROOT + '/_get_video', {
      }, function(response) {
        if(response === null){
          $.growl.error({ message: 'No Response'});
          $('#currentlyPlaying').val('Nothing playing');
          // update_time();
        }else{
          console.log(response.video);
          data.set('playing_video', response.video);

          // $('#currentlyPlaying').val(response.result.filename);
// 
          // length = response.result.length;
          // played = response.result.played
          // $('#video_progress').prop('aria-valuemax', response.result.length);
          // $('#video_progress').prop('aria-valuenow', response.result.played);
          // 
          // set_progress();

          // set_play_state(response.result.playing);

        }
      });
}

/** dunno if i like this function name
 * 
 */
function update_display(video){
  $('#currentlyPlaying').val(video.title);
}

/**
 * remove duplicates
 */
function clean_video_list(){
  $.getJSON($SCRIPT_ROOT + '/_clean_video_list', {

    }, function(response) {
        if(response.length===0){
          console.log('no response');
          $.growl.error({ message: 'No Response'});
        }else{
          $.growl.notice({ message: 'Cleared video list' });
          data.set('videos', response.videos);
        }
    });
}

function delete_video(id){
  // not sure if this will convert js true to python True so stringing
  console.log('in here')
  file_also = 'False';
  if(confirm('file also?')){
    file_also = 'True';
  }
  $.getJSON($SCRIPT_ROOT + '/_delete_video', {
      videoId: id,
      delete_file: file_also
    }, function(response) {
        $.growl.notice({ message: 'Deleting ' + response.video.title });
        // TODO: check for data
        data.set('videos', response.videos);
        // if(response.result.length===0){
        //   console.log('no response');
        //   $.growl.error({ message: 'Couldn\'t delete'});
        // }else{
        //   $.growl.notice({ message: 'Deleting ' + response.result.title });
        //   // return data.videos from _delete_video
        //   // data.set('videos', response.videos);
        //   get_list();
        //   console.log(response.result);
        // }
    });
}

function get_play_targets(){
  $.getJSON($SCRIPT_ROOT + '/_get_play_targets', {}, function(response) {
        if(response.result.length===0){
          console.log('no response');
          $.growl.error({ message: 'no play targets'});
        }else{
          $.growl.notice({ message: 'found play targets' });
          $('#play_targets').empty()
          $.each(response.result, function(i, val){
            $('#play_targets').append(new Option(val.name, val.uuid));
          });
          console.log(response.result);
        }
    });
}

function play_video(id){
    $.getJSON($SCRIPT_ROOT + '/_play_video', {
        videoId: id,
        addedBy: $('#username').val(),
      }, function(response) {
          if(response.length===0){
            console.log('no response');
            $.growl.error({ message: 'Couldn\'t add'});
          }else{
            data.set('queue', response.queue);
            data.set('playing_video', response.video);
            $.growl.notice({ message: 'Adding ' + response.video.title });

            console.log(response.result);
          }
      });
}

function get_file_info(videoId){
  // todo: store file info in db, get width, height file size and black bar status
  $.getJSON($SCRIPT_ROOT + '/_get_file_info', {
        videoId: videoId
    }, function(response) {
      
      if(response.length===0){
        $.growl.error({ message: 'something shat itself' });
      }else{
        // $.growl.notice({ message: 'file info ' + response.result });
        $('.video_info_'+videoId).html(JSON.stringify(response.video.file_properties));
        console.log(response);
      }
    });
}

function convert_video(videoId){
  $.getJSON($SCRIPT_ROOT + '/_convert_video', {
    videoId: videoId
}, function(response) {
  
  if(response.result.length===0){
    $.growl.error({ message: 'something shat itself' });
  }else{
    // $.growl.notice({ message: 'file info ' + response.result });
    console.log(response.result);
  }
});
}

function download_video(){
  $.growl.notice({ message: 'Downloading ' + $('#youtubeUrl').val() });
  $.getJSON($SCRIPT_ROOT + '/_download_video', {
        url: $('#youtubeUrl').val(),
        addedBy: $('#username').val(),
    }, function(response) {
      console.log('finished downloading')
      if(response.length===0){
        $.growl.notice({ message: 'Some kind of error downloading ' + $('#youtubeUrl').val() });
      }else{
        $.growl.notice({ message: 'Succeeded downloading ' + response.video.title });
        data.set('videos', response.videos);

      }
    });
}

function clear_queue(){
  $.getJSON($SCRIPT_ROOT + '/_clear_queue', {
  }, function(response) {
      if(response) {
        $.growl.notice({ message: "Cleared Queue" });
        data.set('queue', []);
        // $('#queue').html('');
      } else {
        $.growl.error({ message: "Something broke clearing queue" });
      }
  });
}

/** get the current queue */
function process_queue(){
  $.getJSON($SCRIPT_ROOT + '/_process_queue', {
  }, function(response) {
      if(response.result.length===0) {
        console.log('nothing queued')
        
      } else {
        
      }
  });
}

function set_queue_position(order){
  $.getJSON($SCRIPT_ROOT + '/_set_queue_position', {
    order: order
  }, function(response) {

      if(response.result.length===0) {
        console.log('blarp')
      } else {
        
      }
  });
}

/** get the current queue */
function get_queue(){
    $.getJSON($SCRIPT_ROOT + '/_get_queue', {
    }, function(response) {
        if(response.queue.length===0) {
          data.set('queue', []);
        } else {
          data.set('queue', response.queue);
        }
    });
}

function scan_folder(){
  $.getJSON($SCRIPT_ROOT + '/_scan_folder', {
  }, function(response) {

      if(response.files.length===0) {
        console.log('no files');
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
  }, function(response) {
    data.set('videos', response.videos);
  });
}

/**
 * get the video list and populate the controls that manage it,
 * currently just #videoUL
 */
function get_list(){
    $.getJSON($SCRIPT_ROOT + '/_list_videos', {
        // test: 'test',
    }, function(response) {
      data.set('videos', response.videos);
    });
}

function draw_video_list(videos){
  var videoULLi = '';

  if(videos.length===0)
    videoULLi='';
  else{
    $.each(videos, function(i, val) {
      length = false;
      try{
        if(!length){
          
          length = val.file_properties.duration;
        }
      }
      catch{}

      try{
        if(!length){
          // TODO: convert to seconds
          arr =  val.file_properties.tags.DURATION.split(':')
          length = parseInt(arr[0]) * 60 * 60 + parseInt(arr[1]) * 60 + parseFloat(arr[2])
          // length = val.file_properties.tags.DURATION;
        }
      }
      catch{}

      videoULLi += '<li class="align-items-center"><a>' + 
        val.title + ' ' + length + ' <i>' + val.addedBy + '</i><br>' + val.filename + ' <span class="badge badge-primary badge-pill">' + val.rating + '</span><br>'+
        'File: <span class="video_info_' + val.videoId + '")">'+JSON.stringify(val.file_properties)+'</span>' + 
        '</a>' +
        '<button class="btn" onclick="play_video(\''+val.videoId+'\')">play now</button>'+
        '<button class="btn" onclick="queue_video(\''+val.videoId+'\')">queue</button>'+
        '<button class="btn" onclick="if(confirm(\'delete '+escape(val.title)+'?\')){ delete_video(\''+val.videoId+'\'); }">delete</button>' +
        '<button class="btn" onclick="get_file_info(\''+val.videoId+'\')">get file info</button>' +
        '<button class="btn" onclick="if(confirm(\'convert '+escape(val.title)+' to h264 1080p?\')){ convert_video(\''+val.videoId+'\'); }">convert video</button>' +
        '<button onclick="rate('+val.videoId+',1)">1</button><button onclick="rate('+val.videoId+',2)">2</button><button onclick="rate('+val.videoId+',3)">3</button><button onclick="rate('+val.videoId+',4)">4</button><button onclick="rate('+val.videoId+',5)">5</button>'+
        '</li>'
    });
  }
  $('#videoUL').html(videoULLi);

  searchUL('videoSearch', 'videoUL') 
}