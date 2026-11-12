%Reading the image of the line
img = imread("ligne3.jpg");

%Compressing the image
img = imresize(img,0.2); 

%Converting the image to grayscale 
img = rgb2gray(img); 

width = size(img,2); %width of the image
height = size(img,1); %height of the image
    
%filtering the image with a median filter to remove noise
median_img = medfilt2(img);

img_chosen = median_img;

%Using the canny edge detector in order to detect the line

threshold_canny = 0.5;%chosing the threshold
img_canny = edge(img_chosen,'canny', threshold_canny); 

filtered_img = img_canny;

row_coordinates = zeros(height,2); %empty array to store the coordinates of the ligne (i,j) of the first pixel and (i,j2) of the last pixel
beg_col = floor(width/5); %column from which we start looking for 2 pixel distant from 5    
beg_row = 1; %row from which we start looking for a difference of epsilon between 2 pixel distant from 5

tmp = double(filtered_img); %converting filtered_img from uint8 to double because uint8 type can't be negative
for i = beg_row : height
    for j = beg_col : (width-3)
        if abs(tmp(i,j+3) - tmp(i,j)) == 1
            row_coordinates(i,1) = j+3;
            for j2 = j+10 : (width-3)
                if abs(tmp(i,j2+3)-tmp(i,j2)) == 1
                    row_coordinates(i,2) = j2;
                    break
                end
            end
            break
        end
    end
end

%drowing the line 
dessin_ligne = ones(size(filtered_img));
s2 = size(row_coordinates);
for i = beg_row : height
    for j = row_coordinates(i,1) : row_coordinates(i,2)
        dessin_ligne(i,j+1) = 255;
    end
end
    
% figure()
% subplot(1,3,1)
% imshow(img)
% subplot(1,3,2)
% imshow(filtered_img)
% subplot(1,3,3)
% imshow(dessin_ligne,[])


line = zeros(height,1);
for i = 1:height
    line(i,1) = floor((row_coordinates(i,2) + row_coordinates(i,1))/2);
end






% tmp = zeros(size(img));
% for i = 1:height  
%     tmp(i,line(i,1)) = 1;
% end

%Computing the radon transform
% figure();
prefstate = iptgetpref('ImshowAxesVisible');
iptsetpref('ImshowAxesVisible','on')
theta = 0:179;
[R,xp] = radon(filtered_img, theta);
% imshow(R,[],'Xdata',theta,'Ydata',xp,'InitialMagnification','fit') %showing the radon transform of the image
xlabel('\theta (degrees)')
ylabel('x''')
colormap(gca,hot), colorbar
iptsetpref('ImshowAxesVisible',prefstate);

%Step 6: find the image orientation and rotate it
%We take maximum value of each column
V=max(R);
%We sum V(1:90) and V(91:180)
V_total = V(1:90) + V(91:180);
%We look for the index with the maximum value in V
ind_max = find(V_total==max(V_total(1:90)));

%We plot the result with the rotation of ind_max
figure();
subplot(1,3,1)
imshow(img_chosen)
title('Median filtered image')
subplot(1,3,2)
imshow(R,[],'Xdata',theta,'Ydata',xp,'InitialMagnification','fit')
title('radon transform')
subplot(1,3,3)
img_chosen = imrotate(img_chosen, -ind_max);
imshow(img_chosen);
title('rotated image')

music = [1:10000;1:10000];
%music = music.';
music = sin(440*music);

sound(sound1(pi/4,music));
%pi/2 = droite, 0 = gauche



%-The image is compressend and filtered (with a median filter)
%-Then we use the canny edge detector to detect edges (gives a binary image)
%-Looking at each line of the image and consider the first different pixel
%the left side of the line (and second the right side)
%-Finaly we use the ardon transform to find the angle between the line and
%the vertical axe



function interactiveLine(imgEdge,imgRadon,N);
%FUNCTION interactiveLine(imgEdge,imgRadon,N);
%   Parameters:
%     - imgEdge: Edge image
%     - imgRadon: Radon transform of imgEdge
%     - N: Number of lines to be drawn

% Display the radon transform
figure;
imshow(imgRadon,[]);
colormap(jet);

% Click some points
disp('Select as many points as required')
[X,Y] = ginput(N);

% Display crosses at selected points
hold on;
plot(X,Y,'mx');
hold off;

% Obtain some dimensions
[h w]= size(imgEdge);
[hr wr] = size(imgRadon);

% Display the edge image with overlaid lines
figure;
imshow(imgEdge,[]);
hold on;
for i=1:N,
    [LX LY] = tracedroite(w,h,wr,hr,X(i),Y(i));
    plot(LX,LY);
end
hold off;
end

function [X, Y] = tracedroite(w, h, wr, hr, x, y)

t = [-hr:hr];


a = (x/double(wr))*pi;

cs = cos(a);
sn = sin(a);

d = y-hr/2;

X = w/2 + cs*d - sn*t;
Y = h/2 - sn*d - cs*t;

end


function t = sound1(angle,music)
    cos(angle);

    music(1,:) = music(1,:).*cos(angle);
    %music(1,:) = zeros(1,10001)
    music(2,:) = music(2,:).*sin(angle);
    t = music;

end


