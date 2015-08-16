#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
sub2xml - convert ass-subtitles to Premiere Pro-prtl + FCP-XML files
creates one track per style
(c) 2015 - Yasar L. Ahmed

requires:   pytitle (ass-parsing)
            xml/prtl templates (supplied, see /templates)
            pillow (for string width estimation)

usage:
sub2xml.py mytitle.ass
'''


import sys
import os
import time
import warnings
import subprocess
import xml.etree.ElementTree as ET

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        import ass
    except ImportError:
        print('Error - python-ass not found, please install python-ass')
        exit()

try:
    from PIL import ImageFont
    try:
        font = ImageFont.truetype("arial.ttf", 46)
    except IOError:
        font = ImageFont.truetype("DroidSans.ttf",46) # for testing
except ImportError:
    print('Error - pillow not found, please install pillow')
    exit()


input_sub = sys.argv[1]

#inputs
start_dir = os.path.dirname(os.path.realpath(sys.argv[0]))

template_dir = start_dir  + "/templates/"

submaker_xml_template = template_dir + "submaker_xml_trackless.xml"
submaker_clip_template = template_dir + "submaker_clip_template.xml"
submaker_title_template = template_dir + "submaker_title_template.prtl"

#outputs
output_xml_file_name = 'subtitle_proj.xml'
cur_time = str(time.strftime("%Y-%m-%d_%H%M-%S"))

source_dir = os.path.dirname(os.path.realpath(input_sub))
output_proj_dir = source_dir + '/' + 'premiere_proj'+ "_" + cur_time[-7:]
output_subs_dir = output_proj_dir + '/' + 'subs'

os.mkdir(output_proj_dir)
os.mkdir(output_subs_dir)

def setup_proj_xml(inp):
    '''
    returns patched up xml object of proj_xml
    '''
    frate = 25
    res = (1920,1080)
    proj_xml = ET.parse(submaker_xml_template)
    proj_xml.find(".//width").text = str(res[0])
    proj_xml.find(".//height").text = str(res[1])
    proj_xml.find(".//timebase").text = str(frate)
    return(proj_xml)


def main():
    all_files = os.listdir(template_dir)
    presets = []
    for file in all_files:
        if file.endswith('.prtl'):
            presets.append(file)  
    preset = "submaker_title_template.prtl"
    clip_xml = ET.parse(submaker_clip_template)
    proj_xml = setup_proj_xml(submaker_xml_template)
    video_node = proj_xml.find(".//video")
    # create a base track for video placement
    base_track = make_track('VIDEO')
    video_node.append(base_track)
    subs, sub_styles = sub_load(input_sub)
    tmplen = len(subs)
    for i in sub_styles.keys():
        # create one track per style
        vt = make_track(i)
        video_node.append(vt)
    styles = list(sub_styles.keys())
    track_nodes = proj_xml.find('.//video')
    total_subs = len(subs)
    problematic_titles = []
    for i in subs:
        sub_text = i.text
        stl_data = sub_styles[i.style]
        sub_number = subs.index(i)
        sub_number_str = str(subs.index(i))
        progress = (sub_number /  total_subs) * 100
        sys.stdout.write(str('\r[{0}] {1}%'.format('#'*int(progress/2), round(progress,1))))
        sys.stdout.flush()
        prtl_fname = 'sub_' + sub_number_str.zfill(6) + ".prtl"
        prtl_abs_fname = output_subs_dir + "//" + prtl_fname
        title, prtl_warning = generate_prtl(sub_text, stl_data, preset)
        # encoding needs to be UTF16 without BOM = UTF-16LE
        title.write(prtl_abs_fname , encoding='UTF-16LE', xml_declaration=True)
        f_start,f_end = get_time(i)
        clip_entry = generate_clip_entry(f_start, f_end, prtl_fname)
        if prtl_warning:
            ps_tc = convert_fn_to_tc(f_start)
            problematic_titles.append((prtl_fname, ps_tc, sub_text))
        # select the correct track
        for track in track_nodes:
            try:
                # match track id with style name
                if track.attrib['id'] == str(subs[sub_number].style):
                    track.append(clip_entry)
            except:
                KeyError
    input_sub_fname = input_sub.split("\\")[-1]
    fname_proj_xml = input_sub_fname[0:-3] + 'xml'
    abs_fname_proj_xml = output_proj_dir + "/" + 'project_' + fname_proj_xml
    proj_xml.write(abs_fname_proj_xml, xml_declaration=True, encoding="UTF-8")
    win_output_proj_dir = str(output_proj_dir).replace('/','\\')
    win_output_subs_dir = str(output_subs_dir).replace('/','\\')
    if len(problematic_titles) != 0:
        log_file_handle = output_proj_dir + '//' + 'problematic_titles.txt'
        log_file = open(log_file_handle, 'w')
        for i in problematic_titles:
            ps_fname = str(i[0])
            ps_time = str(i[1]) 
            ps_txt = str(i[2])            
            log_file.write(ps_fname + '\n')
            log_file.write(ps_time + '\n')
            log_file.write(ps_txt + '\n\n')
        log_file.close()
        sys.stdout.write('\n\n ---WARNING!---')
        sys.stdout.write('\n Problematic titles were detected and logged.')
        sys.stdout.write('\n Please check problematic_titles.txt manually.')
    sys.stdout.write('\n\n XML-file: ' + str(fname_proj_xml))
    sys.stdout.write('\n Project folder: ' + win_output_proj_dir)
    sys.stdout.write('\n Subs folder: ' + win_output_subs_dir)
    sys.stdout.write('\n\n ---FINISHED---')
    input('\n\n Press <ENTER> to open project dir')
    subprocess.Popen('explorer {}'.format(win_output_proj_dir))


def generate_clip_entry(start, end, inp):
    '''
    input start/end-times in frames
    return xml-object containing clip-entry
    '''
    myclip = ET.parse(submaker_clip_template)
    mycliptree = myclip.getroot()
    mycliptree.attrib['id']= inp
    mycliptree.find('start').text = str(start)
    mycliptree.find('end').text = str(end)
    mycliptree.find('in').text = str(start)
    mycliptree.find('out').text = str(end)
    mycliptree.find('name').text = inp
    path = output_subs_dir
    url = path + "/" + inp
    f = mycliptree.find('file')
    f.set('id', inp)
    f.find('pathurl').text = str(url)
    return(mycliptree)


def sub_load(inp_fname):
    '''
    input = ass subtitle file
    output = subtitle instance and dict with meta_data for easy access (for later)
    '''
    subs_stl = {}
    #f = io.open(inp_fname, "rb")
    #doc = ass.parse(f)
    with open(inp_fname, "r", encoding='utf-8') as f:
        doc = ass.parse(f)
    subs = doc.events
    for i in doc.styles:
        stl_name = i.name
        r = i.primary_color.r
        g = i.primary_color.g
        b = i.primary_color.b
        a = i.primary_color.a
        font_name = i.fontname
        font_size = i.fontsize
        subs_stl.update({str(stl_name): {'r':r, 'g':g, 'b':b, 'a':a,
                                          'font_name':font_name, 
                                          'font_size':font_size}})
    return(subs, subs_stl)


def convert_fn_to_tc(inp):
    '''
    input = frame number
    output = string with HH:MM:SS:FF
    '''
    t_sec = inp//25
    tc_hh = (str(t_sec // 3600)).zfill(2)
    tc_mm = (str(t_sec // 60)).zfill(2)
    tc_ss = (str(t_sec % 60)).zfill(2)
    tc_ff = (str(inp % 25)).zfill(2)
    tc_complete = '{0}:{1}:{2}:{3}'.format(tc_hh, tc_mm, tc_ss, tc_ff)
    return(tc_complete)


def get_time(inp):
    '''
    input = subtitle object
    output = return start and end frame number
    '''
    start_sec = inp.start.seconds
    start_msec = inp.start.microseconds/1000
    end_sec = inp.end.seconds
    end_msec = inp.end.microseconds/1000
    start_frame = int(start_sec*25  + round(start_msec/40))
    end_frame = int(end_sec*25 + round(end_msec/40))
    return(start_frame,end_frame)


def generate_prtl(inp_sub_text, stl_data, inp_template):
    '''
    input = str/text and template
    returns xml-object of title
    '''
    stl_data = stl_data
    template = template_dir + "/" + inp_template
    tree = ET.parse(template)
    root = tree.getroot()
    root.findall('.//TRString')[0].text = inp_sub_text
    r_count = len(inp_sub_text)
    root.findall('.//CharacterAttributes')[0].attrib['RunCount'] = str(r_count)
    tx_width, tx_height = font.getsize(inp_sub_text)
    predicted_width = tx_width * 1.1
    prtl_warn = False
    if predicted_width < 1640:
        new_width = predicted_width
        root.find('.//gSizeX').text = str(new_width)
        #recenter
        x_center = 960 - (new_width/2)
        root.find('.//gCrsrX').text = str(x_center)
        root.find('.//gSizeY').text = str(80)
    # hack to prevent overfilling/overflow for current template
    # would be better to read text object width and fill it in
    if predicted_width > 3000:
        root.find('.//txWidth').text = str(44) #inp template is 46
        root.find('.//txHeight').text = str(44)
        prtl_warn = True
    return(tree, prtl_warn)


def make_track(track_id, enabled='TRUE', locked='FALSE'):
    '''
    input = name/id of track
    return = XML element of track entry
    '''
    track = ET.Element('track')
    track.attrib['MZ.TrackName'] = track_id #this will be the track name in premiere
    track.append(ET.Element('enabled'))
    track[0].text = enabled
    track.append(ET.Element('locked'))
    track[1].text = locked
    track_id = track_id
    track.attrib['id'] = track_id
    return(track)

main()