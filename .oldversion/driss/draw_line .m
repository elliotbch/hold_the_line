close all
im=imread('ligne.jpg');

figure
ini=rgb2gray(im);


figure

l = imresize(ini,1/8); 


s=imsharpen(l); %sharpen the image
smo= imgaussfilt(s,5); % lissage de l'image
% 
l = edge(smo,'log'); %Trouve les bords en recherchant les passages par zéro après avoir filtré I avec un filtre laplacien de gaussien (LoG).
n=size(l,1); 
m=size(l,2);


for i=(1:n)
    p=0;%second limit
    j=0; %colonnes
    c=0;%compteur
    while (j<m) && (c<2)
        j=j+1;
        if l(i,j)==1 %%si on trouve la première limite
            c=c+1; %on incrémente le compteur
            if c==2
                q=floor((p+j)/2); % q=milieu de la grande ligne
                l(i,q)=1; %tracage de la ligne
            end
            p=j;

   
        end
    end
end

%on se positionne au milieu à la dixième partie de l'image
a=round(n*9/10);
b=round(m/2);
%%si on sinteresse qu'à cette dernière partie, la boucle qu'on vient de
%%faire pour tracer le milieu on peut la faire que pour cette partie

lim=[];
for i=(1:m)
    if l(a,i)==1
        lim(end+1)=i;
    end
    
end
disp(lim); %% lim contient les deux limites et le point du milieu qu'on vient de tracer

l(a,b)=1;%%position de l'utilisateur


Fs = 44100; %fréquence


if (lim(2)<b)
    Fs = 44100;
    t = linspace(0, Fs*2, Fs*2);
    s = sin(2*pi*t*1000);
    Out = [zeros(size(t)); s]';


    Volume    = b-lim(2);
    s        = s .* Volume;
    Out = [zeros(size(t)); s]';

    sound(Out, Fs);


end


if (b<lim(2))
    t = linspace(0, Fs*2, Fs*2);
    s = sin(2*pi*t*1000);
    Volume    = lim(2)-b;
    s        = s .* Volume;
    Out = [s;zeros(size(t))]';

    sound(Out, Fs)
end



imshow(l);

