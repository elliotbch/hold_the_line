close all
im=imread('ligne.jpg');

ini=rgb2gray(im);

figure
% 
l = imresize(ini,1/13); 


s=imsharpen(l); %sharpen the image
smo= imgaussfilt(s,5); % lissage de l'image
% 
l = edge(smo,'zerocross'); %edges
%  
imshow(l)