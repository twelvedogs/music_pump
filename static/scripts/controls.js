var myPlayer = null;
    $(function() {
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

    function raw_command(cmd){
        $.getJSON($SCRIPT_ROOT + '/_raw_command', {
            cmd: cmd,
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
              // url: $('#youtubeUrl').val(),
          }, function(data) {
              if(data.result.length===0){
                console.log('no data')
              }else{
                console.log(data.result);
              }
          });
    }

    function get_song(){
        $.getJSON($SCRIPT_ROOT + '/_get_song', {
          }, function(data) {
            console.log(data)
              if(data === null || data.result === null || data.result.length === 0){
                console.log('no data')
              }else{
                console.log(data.result);
                $('#currentlyPlaying').text(data.result);
              }
          });
    }

    function get_length(){
        $.getJSON($SCRIPT_ROOT + '/_get_length', {
              // url: $('#youtubeUrl').val(),
          }, function(data) {
              if(data.result.length===0){
                console.log('no data')
              }else{
                console.log(data.result);
              }
          });
    }

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

    function get_list(){
        $.getJSON($SCRIPT_ROOT + '/_list_videos', {
            test: 'test',
        }, function(data) {
            var fileList = '';

            if(data.result.length===0) {
              console.log('no files')
              $('#files').html('no files');
            } else {

              $.each(data.result, function(i, val) {
                  fileList += '<a onclick="play_video(\''+val.videoId+'\')">'+val.title+'</a><br>';
              });
              $('#files').html(fileList);
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