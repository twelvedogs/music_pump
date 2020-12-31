/**
 * this could probably be renamed to fillFormFromObject or something more meaningful
 * @param {any} selector container to push data to
 * @param {any} jsonObj object to pull properties from
 * @param {any} htmlEncodeDivs html encode or not when pushing values into divs.  default: true
 * @param {any} attrName attribute name to use for selector, defaults to 'data-paramname'
 */
function set_field_data(selector, jsonObj, htmlEncodeDivs, attrName) {
  // console.log(selector, jsonObj, htmlEncodeDivs, attrName)

  if (!jsonObj) {
      // jqueryError('deserializeTo: jsonObj is undefined');
      console.log('deserializeTo: jsonObj is undefined');
      return;
  }

  if ($(selector).length === 0) {
      jqueryError('deserializeTo could not find container with selector ' + selector);
      return;
  }

  if (htmlEncodeDivs !== false)
      htmlEncodeDivs = true;

  if (!attrName)
      attrName = 'data-paramname';

  $.each(jsonObj, function (i, val) {
      var Value = null;

      //if (typeof val === 'array') {
      //    // load the array into the fields somehow
      //}
      if (typeof val === 'string' || typeof val === 'boolean' || typeof val === 'number') {
          Value = val;
      }
      else if (typeof val === 'object' && val !== null && val.hasOwnProperty('id') && val.id !== null && $('select[' + attrName + '=' + i + ']').length > 0) {
          Value = val.id; //if the id is stored for a select, use that over the text value
      } else if (typeof val === 'object' && val !== null && val.hasOwnProperty('id') && val.id !== null) { // if we've stored extra stuff in this node just grab the selected id
          Value = val.text; //todo: broken??
      } else if (typeof val === 'object' && val !== null && val.hasOwnProperty('paramname') && val.paramname !== null
          && $('input[type=radio][' + attrName + '=' + i + ']').length > 0) {
          Value = val.text;
      }
      else {
          return;
      }

      // if we have a date format it
      if (isISO8061(Value))
          Value = getFormattedDate(new Date(Date.parse(Value)), true);

      // set all matching controls regardless of type
      if (Value !== null && typeof Value !== 'undefined') {
          $(selector + ' textarea[' + attrName + '=' + i + '], ' +
              selector + ' input:text[' + attrName + '=' + i + '], ' +
              selector + ' select[' + attrName + '=' + i + ']').val(Value.toString());                // textarea, text, dropdowns inputs

          if (htmlEncodeDivs) {                                                                       // divs
              $(selector + ' div[' + attrName + '=' + i + ']').html(htmlEncode(Value));
          } else {
              $(selector + ' div[' + attrName + '=' + i + ']').html(Value);
          }

          try {
              if (Value.indexOf('"') === -1) {
                  $(selector + ' input[type=radio][' + attrName + '=' + i + '][value="' + Value + '"]').prop('checked', true);
              }
          }catch(ex){
              // pass;
          }

          // todo: this could probably be less stupid
          if (Value === true || typeof Value === 'string' && Value.toLowerCase() === 'true')
              $(selector + ' input:checkbox[' + attrName + '=' + i + ']').prop('checked', true);      // check boxes
          else
              $(selector + ' input:checkbox[' + attrName + '=' + i + ']').prop('checked', false);     // uncheck boxes
      }
  });
}

/**

* @param {string} selector container selector
* @param {string} attrName attribute name to use as the key, default is data-paramname
* @param {string} postSelector Selector that is appended to the end of the jQuery selector e.g. :not(:checked)
* @returns {object} object containing form fields
*/
function get_field_data(selector, attrName, postSelector) {
  var jsonObj = {};

  if (!attrName)
      attrName = 'data-property';

  if (!postSelector)
      postSelector = '';

  // select all controls with the given attribute name inside the selector
  $(selector + ' [' + attrName + ']' + postSelector).each(function () {
      if ($(this).prop('disabled') !== 'disabled') {
          //this selector gets all radio buttons in form but we only want the checked ones
          if ($(this).attr('type') === 'radio' && !$(this).prop('checked'))
              return;

          var attrValue = $(this).attr(attrName); // get the key name from the attribute

          var crntObj = {};
          // attach any data- properties from the control
          $.each(this.attributes, function (i, val) {
              if (val.name.substring(0, 5) === 'data-')
                  crntObj[val.name.substring(5, val.name.length)] = val.value;
          });

          crntObj.id = $(this).attr('id');

          if ($(this).is('div') || $(this).is('span')) {
              crntObj.text = $(this).html();
          } else if ($(this).attr('type') === 'checkbox') {
              
              // if multiple controls, make an array
              if ($('[name=\'' + $(this).attr('name') + '\']').length > 1) {
                  var obj = {};
                  if ($(this).prop('checked')) {
                      obj[$(this).attr('name')] = $(this).val();
                  } else {
                      obj[$(this).attr('name')] = '';
                  }

                  // if other checkboxes with this name have already been stored add it to their value for the key
                  if (jsonObj[attrValue]) {
                      jsonObj[attrValue].push(obj);
                  } else {
                      jsonObj[attrValue] = [obj];
                  }

              } else {
                  if ($(this).prop('checked')) {
                      crntObj.text = true;
                  } else {
                      crntObj.text = '';
                  }
              }
              
          } else if ($(this).is('select')) {
              crntObj.id = $(this).val(); // todo: this will clash with the id set for the actual control
              if (crntObj.id !== '') { // if the value was empty we were still getting the text which was screwing up the display with stuff like 'Please Select...' as the value
                  crntObj.text = $(this).find('option:selected').text();
              } else {
                  crntObj.text = '';
              }
          } else {
              crntObj.text = $(this).val();
          }

          jsonObj[attrValue] = crntObj;
      }
  });

  return jsonObj;
}