% Bloc MATLAB Function « fast/findsound » extrait de simulink/projects5.slx
% (copie en lecture seule pour consulter l'algorithme sans MATLAB ;
%  la source de référence reste le modèle Simulink).

function [left, right, imgt] = findsound(img,c,tresh, monot)
%delete all the non line color imager and put the line in full white
S = size(img);
for l=1:S(1,1)
    for x=1:S(1,2)
        tp=img(l,x,:);
        if manorm(double([tp(1),tp(2),tp(3)])-c(1,:))>tresh
            img(l,x,:) = [0,0,0];
        else
            img(l,x,:) = [255,255,255];
        end

    end
end

%grayify the image and process simple median filter to make sampling more
%precise
img = rgb2gray(uint8(img));
img = medfilt2(img,[16,16]);

imgt = img;
%calculate the line angle with the vertical
coef=regressionlineair(img);
angle = ( atan(abs(coef))+pi/2)*sign(coef);
angle * 180/pi;
%output amplitudes ratios for left and right based on trigonometriques
%proportions in order that the sum made 1
if angle > pi/4
   left = 0;
   right = 1;
elseif angle < -pi/4
   left = 1;
   right = 0;
else
   left = sin((angle+pi/4))^2;
   right = cos(angle+pi/4)^2;
end
end



function coef = regressionlineair(img)
    %do some linear regression and return the line angle
    S = size(img);
    Points = [];
    for l=1:S(1,1)
       Points = [ Points trouvermilieux(img,l)];
    end
    x = Points(1,:);
    x = transpose(x);
    s = size(x);
    un = ones(s(1,1),1);
    y = Points(2,:);
    y = transpose(y);
    x = double(x);
    y = double(y);
    p = polyfit(x,y,1);
    coef = p(1,1);
end


function pix = trouvermilieux(img, l)
    %find all middles in same colored segments
    S = size(img);
    c = 1;
    temp = [];
    while c<S(1,2)
        while img(l,c,:)==0 & c < S(1,2)
            c=c+1;
        end

        debut = c;
        while img(l,c,:)>0 & c < S(1,2)
            c=c+1;
        end
        fin = int32(c-1);
        if c < S(1,2)
            vec = [l int32((debut+fin)/2)];
            vec = transpose(vec);
            temp = [ temp vec];
        end
        
    end
    pix = temp;
end

function v = manorm(u)
    %basic eucledian norm
    v = sqrt(double(u(1,1).^2+u(1,2).^2+u(1,3).^2));
end
