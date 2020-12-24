
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
  // sucks if you don't do this
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
    // videojs("example_video_1").ready(function(){
    //     myPlayer = this;

    //     // EXAMPLE: Start playing the video.
    //     console.log('playing')
    //     // myPlayer.play();

    // });
});

function isEmptyOrSpaces(str){
  return str === null || str.match(/^\s*$/) !== null;
}

function update_queue(queue){
  queue_html = '<ul id="queue-list" class="queue-list">';
  $.each(queue, function(i, queue_video) {
    queue_html += '<li><a onclick="set_queue_position(\'' + queue_video.order+'\')" title="Added by: ' + queue_video.addedBy + '">'+
    queue_video.title + '</a></li>';
  });

  $('#queue').html(queue_html);

  // TODO: don't scroll bottom if not at bottom?  might be fine actually
  $('#queue').scrollTop($('#queue')[0].scrollHeight);

}

// don't really know what to call this, Storage_Object_With_Listeners is pretty clunky
class Data{
  constructor() {

    this.length = 0; // current song length in seconds, should use playing_video.length instead
    this.time_start = null; // seconds since epoch that this song started playing
    
    this.videos = {};
    // should i just store the last updated time on every property?  might make it easier, if i can just get back "data" from the server then use
    // it to update the properties automatically if they're newer it might simplify things
    this.time_videos_last_updated = get_seconds_since_epoch(); 
    this.queue = {};
    this.time_queue_last_updated = get_seconds_since_epoch();
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
data.add_listener('queue', function(){data.set('time_queue_last_updated', get_seconds_since_epoch());});
data.add_listener('videos', draw_video_list_new);
data.add_listener('videos', function(){data.set('time_videos_last_updated', get_seconds_since_epoch());});
data.add_listener('playing_video', update_interface); // this might be called after video has started?

function update_interface(updated){
  // if(!old || updated.videoId !== old.videoId){
  //   console.log('new video should be doing stuff', updated);
  //   // data.set('time_start', get_seconds_since_epoch()); // only to be pulled from server
  // }

  if(data.playing_video){
    $('#currentlyPlaying').val(data.playing_video.title);
  }else{
    $('#currentlyPlaying').val('Nothing playing');
  }
  
}

function get_seconds_since_epoch(){
  return Math.round((new Date()).getTime() / 1000);
}

function update_playing(){
  if(data.playing_video!== null){
    seconds_since_epoch = get_seconds_since_epoch();
    if(!data.playing_video.length){
      console.log('video length not set')
    }
    set_progress(seconds_since_epoch - data.time_start, data.playing_video.length);
  }
}

// repeat with the interval in ms
progress_update_timer = setInterval(update_playing, 1000);
get_currently_playing = setInterval(get_video, 5000);

// after 5 seconds stop
// setTimeout(() => { clearInterval(timerId); alert('stop'); }, 5000);

function set_progress(played, length){
  // console.log('setting to', played, length);
  $('#video_current_time').text(played);
  $('#video_length').text(length);
  $('#video_progress').css('width','' + played/length * 100 + '%');
}

function queue_video(id){
  $.getJSON($SCRIPT_ROOT + '_queue_video', {
      videoId: id,
      addedBy: $('#username').val(),
    }, function(response) {
        if(response.length===0){
          console.log('no response');
          $.growl.error({ message: 'Couldn\'t add'});
        }else{
          data.set('queue', response.queue);
          // data.set('playing_video', response.video);
          $.growl.notice({ message: 'Queueing ' + response.video.title });
        }
    });
}

// player controls
function stop(){
  $.getJSON($SCRIPT_ROOT + '/_stop', {
    }, function(response) {
        if(response.length===0){
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
        data.set('time_start', get_seconds_since_epoch()); // might actually be able to pull from server
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
        data.set('time_start', get_seconds_since_epoch()); // might actually be able to pull from server
        data.set('playing_video', response.video);
        data.set('queue', response.queue);
        // TODO: set queue position
      }
    });
}
function play(){
  $.getJSON($SCRIPT_ROOT + '/_play', {
    }, function(response) {
        if(response.length===0){
          console.log('no response')
        }else{
          console.log(response);
        }
    });
}

function play_pause(){
  $.getJSON($SCRIPT_ROOT + '/_play_pause', {
    }, function(response) {
        if(response.length===0){
          console.log('no response')
        }else{
          console.log(response);
        }
    });
}




/**
 * get current playing video & play time
 */
function get_video(){
  $.getJSON($SCRIPT_ROOT + '/_get_video', {
      queue_last_updated: data.time_queue_last_updated,
      files_last_updated: data.time_videos_last_updated
    }, function(response) {
      if(response === null){
        $.growl.error({ message: 'No Response'});
        data.set('playing_video', null);
        // TODO: move to listener
        // $('#currentlyPlaying').val('Nothing playing');
        // update_time();
      }else{
        data.set('playing_video', response.video);
        data.set('time_start', response.time_started);
        if(response.queue)
          data.set('queue', response.queue);
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
  file_also = 'False';
  if(confirm('file also?')){
    file_also = 'True';
  }
  $.getJSON($SCRIPT_ROOT + '/_delete_video', {
      videoId: id,
      delete_file: file_also
    }, function(response) {
        $.growl.notice({ message: 'Deleting ' + response.video.title });
        data.set('videos', response.videos);
    });
}


function set_play_target(device_id){
  $.getJSON($SCRIPT_ROOT + '/_set_play_target', {
    device_id, device_id
  }, function(response) {
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

function set_play_target(device_id){
  if(!device_id)
    alert('No Device Selected');

  $.getJSON($SCRIPT_ROOT + '/_set_play_target', {
    device_id: device_id
  }, function(response) {
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
        console.log('get file info', response);
      }
    });
}

function convert_video(videoId){
  $.getJSON($SCRIPT_ROOT + '/_convert_video', {
    videoId: videoId
}, function(response) {
  
  if(response.length===0){
    $.growl.error({ message: 'something shat itself' });
  }else{
    // $.growl.notice({ message: 'file info ' + response.result });
    console.log(response);
  }
});
}

function download_video(){
  $.growl.notice({ message: 'Downloading ' + $('#youtubeUrl').val() });
  $.getJSON($SCRIPT_ROOT + '/_download_video', {
        url: $('#youtubeUrl').val(),
        addedBy: $('#username').val(),
    }, function(response) {
      console.log('finished downloading');
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

function set_queue_position(order){
  $.getJSON($SCRIPT_ROOT + '/_set_queue_position', {
    order: order
  }, function(response) {
      if(response.length===0) {
        console.log('blarp')
      } else {
        if(response.queue)
          data.set('queue', response.queue);
        if(response.video)
          data.set('crnt_video', response.video);
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
function update_video_popup(video){
  $.each(video, function(key ,prop){

    $('.' + key).val(prop);
  })
}

data.add_listener('video_popup_crnt_video', update_video_popup);

var video_popup_crnt_video = null;
function video_popup(videoId){
  $.getJSON($SCRIPT_ROOT + '/_get_video_by_id', {
    videoId: videoId,
  }, function(response) {
    data.set('video_popup_crnt_video', response);
    video_popup_crnt_video = response;
  });

  $('#videoModal').modal()
}

function draw_video_list_new(videos){
  var videoULLi = '';

  if(videos.length===0)
    videoULLi='';
  else{
    $.each(videos, function(i, video) {
      if(video.title.length<60){
        title = video.title;
      }else{
        title = video.title.substring(0,57) + '...';
      }

      
      // a tag is used for search text
      videoULLi += '<li class="align-items-center"><span class="video-info">' +
        '<a style="display: none; width: 0px">' + video.title + '</a> ' + title +
        '<div style="float: right">' +
        '<span class="control" onclick="play_video(\''+video.videoId+'\')">play</span>' +
        '<span class="control" onclick="queue_video(\''+video.videoId+'\')">queue</span>' +
        '<span class="control" onclick="video_popup(\''+video.videoId+'\')">actions</span>' +
        '<span class="badge badge-primary badge-pill">' + video.rating + '</span>' +
        '</div>' +
        '</span></li>'
    });
  }
  $('#videoUL').html(videoULLi);
  searchUL('videoSearch', 'videoUL');
}

function draw_video_list(videos){
  var videoULLi = '';

  if(videos.length===0)
    videoULLi='';
  else{
    $.each(videos, function(i, val) {
      var codec= 'Dunno';
      try{
        codec=val.file_properties.codec_name
      }catch{}
      videoULLi += '<li class="align-items-center"><a>' + 
        val.title + ' ' + val.length + ' <i>' + val.addedBy + '</i><br>' + val.filename + ' <span class="badge badge-primary badge-pill">' + val.rating + '</span><br>'+
        'Codec: <span class="video_info_' + val.videoId + '")">'+codec+'</span>' + 
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
    searchUL('videoSearch', 'videoUL');
}
 

  
