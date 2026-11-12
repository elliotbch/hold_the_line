close all
im=imread('ligne.jpg');
l=rgb2gray(im);
figure
imshow(l)


R3 = edge(l,'Roberts');
R4 = edge(l,'log');
R5 = edge(l,'zerocross');
R6 = edge(l,'canny');


tiledlayout (1,5)



nexttile
imshow(R3)
title('Roberts Filter')

nexttile
imshow(R4)
title('log Filter')

nexttile
imshow(R5)
title('zerocross Filter')

nexttile
imshow(R6)
title('Canny Filter')


