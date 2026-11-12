I = imread('line.jpeg');
imshow(I)
Ibis=I;
A = size(I);
l = A(1,1);
h = A(1,2);
k = A(1,3);
if mod(l,2)>0
    I(l,:)=[];
end
if mod(h,2)>0
    I(h,:)=[];
end
A = size(I);
l = A(1,1);
h = A(1,2);
for i=2:l-1
    for j=2:h-1
        for g=1:k
            I(i,j,g)=(Ibis(2*fix(i/2),2*fix(j/2),g)+Ibis(2*fix(i/2)+1,2*fix(j/2),g)+Ibis(2*fix(i/2),2*fix(j/2)+1,g)+Ibis(2*fix(i/2)+1,2*fix(j/2)+1,g))/4;  
            %disp([i j g])
        end
    end
end
Itris = I(1:l/2,1:h,:);

for i=1:l
    if mod(i,2)==0
        Itris(i/2,:,:)=I(i,:,:);
    end
end
I = Itris;
%imshow(I)
Itris = [];
for j=1:h
    if mod(j,2)==0
        disp(j);
        Itris(:,j/2,:)=I(:,j,:);
    end
end
I = Itris;
A = size(I);
l = A(1,1);
h = A(1,2);
k = A(1,3);
% for j=1:h
%     if mod(j,2)>0
%         I(:,j)=[];
%     end
% end

disp(size(Ibis))
disp(size(I))
disp(size(Itris))
imshow(I)
%disp(size(I)(1))